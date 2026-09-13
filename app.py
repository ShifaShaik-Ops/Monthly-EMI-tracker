import sqlite3
from datetime import date
import pandas as pd
import streamlit as st

DB = "debt_manager.db"

st.set_page_config(
    page_title="Debt & Cashflow Command Center",
    page_icon="💰",
    layout="wide",
)

# -----------------------------
# Database
# -----------------------------
def db():
    conn = sqlite3.connect(DB, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def setup_database():
    conn = db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS loans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            emi REAL DEFAULT 0,
            remaining_months INTEGER DEFAULT 0,
            emi_day INTEGER DEFAULT 1,
            foreclosure_amount REAL DEFAULT 0,
            foreclosure_charge REAL DEFAULT 0,
            active INTEGER DEFAULT 1,
            notes TEXT DEFAULT ''
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            balance REAL DEFAULT 0,
            minimum_due REAL DEFAULT 0,
            due_day INTEGER DEFAULT 1,
            active INTEGER DEFAULT 1
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT UNIQUE,
            planned REAL DEFAULT 0,
            active INTEGER DEFAULT 1
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            payment_date TEXT,
            category TEXT,
            description TEXT,
            amount REAL DEFAULT 0
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS foreclosures (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            loan_id INTEGER,
            foreclosure_date TEXT,
            amount REAL DEFAULT 0,
            charge REAL DEFAULT 0,
            status TEXT DEFAULT 'Planned',
            funded_by TEXT DEFAULT 'Friend',
            FOREIGN KEY(loan_id) REFERENCES loans(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS card_rotations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rotation_date TEXT,
            card_id INTEGER,
            amount REAL DEFAULT 0,
            fee REAL DEFAULT 0,
            notes TEXT DEFAULT '',
            FOREIGN KEY(card_id) REFERENCES cards(id)
        )
    """)

    try:
        cur.execute("ALTER TABLE foreclosures ADD COLUMN funded_by TEXT DEFAULT 'Friend'")
    except sqlite3.OperationalError:
        pass

    defaults = {
        "monthly_salary": "65000",
        "future_salary": "75000",
        "future_salary_start": "2026-11-01",
        "pf_monthly": "1800",
        "friend_help_amount": "400000",
        "friend_balance": "400000",
        "friend_amount_used": "0",
        "friend_help_enabled": "0",
        "friend_repayment_mode": "Step-up",
        "friend_target_date": "2028-03-31",
        "starting_cash": "20000",
        "bonus_current_month": "0",
        "cheq_fee_per_card": "2000",
        "forecast_start": "2026-10-01",
    }
    for k, v in defaults.items():
        cur.execute(
            "INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)",
            (k, v)
        )

    loans = [
        ("Fibe", 9890, 6, 4, 63924, 0, 1, ""),
        ("Stashfin", 4199, 11, 2, 39058, 0, 1, "Rotatable only if needed"),
        ("Kredit Bee", 9219, 5, 2, 53630, 0, 1, ""),
        ("Branch", 2488, 4, 28, 12440, 0, 1, ""),
        ("Moneyview", 3764, 5, 3, 21808, 979, 1, ""),
        ("Poonawala Fincorp", 6507, 21, 5, 0, 0, 1, "No foreclosure option"),
        ("Instamoney", 5616, 2, 1, 11000, 0, 1, "Rotatable only if needed"),
        ("Kissht", 1583, 8, 7, 14516, 131, 1, ""),
        ("LoanTap", 5276, 1, 1, 10669, 480, 1, ""),
        ("Flexipay", 6000, 23, 26, 103168.29, 0, 1, ""),
    ]
    for row in loans:
        cur.execute("""
            INSERT OR IGNORE INTO loans
            (name,emi,remaining_months,emi_day,foreclosure_amount,foreclosure_charge,active,notes)
            VALUES(?,?,?,?,?,?,?,?)
        """, row)

    cards = [
        ("Axis", 60000, 2000, 1, 1),
        ("HDFC", 29656.34, 1816, 28, 1),
        ("DBS", 36000, 1089.79, 1, 1),
    ]
    for row in cards:
        cur.execute("""
            INSERT OR IGNORE INTO cards
            (name,balance,minimum_due,due_day,active)
            VALUES(?,?,?,?,?)
        """, row)

    expenses = [
        ("Rent", 15000),
        ("Fuel", 2000),
        ("Groceries", 2000),
        ("Miscellaneous", 2000),
        ("JioFiber", 1200),
        ("Salon", 2000),
    ]
    for name, amount in expenses:
        cur.execute(
            "INSERT OR IGNORE INTO expenses(category,planned,active) VALUES(?,?,1)",
            (name, amount)
        )

    conn.commit()
    conn.close()

def get_setting(key, default=""):
    conn = db()
    row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else default

def get_setting_float(key, default=0.0):
    try:
        return float(get_setting(key, default))
    except Exception:
        return float(default)

def get_setting_bool(key, default=False):
    v = str(get_setting(key, "1" if default else "0")).strip().lower()
    return v in ("1", "true", "yes", "on")

def set_setting(key, value):
    conn = db()
    conn.execute(
        "INSERT INTO settings(key,value) VALUES(?,?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, str(value))
    )
    conn.commit()
    conn.close()

def money(x):
    try:
        return f"₹{float(x):,.0f}"
    except Exception:
        return "₹0"

def money2(x):
    try:
        return f"₹{float(x):,.2f}"
    except Exception:
        return "₹0.00"

def qdf(sql, params=()):
    conn = db()
    df = pd.read_sql_query(sql, conn, params=params)
    conn.close()
    return df

setup_database()

# -----------------------------
# Data helpers
# -----------------------------
def loans_df():
    return qdf("""
        SELECT * FROM loans
        WHERE active=1
        ORDER BY CASE WHEN remaining_months=0 THEN 1 ELSE 0 END, emi DESC
    """)

def cards_df():
    return qdf("SELECT * FROM cards WHERE active=1 ORDER BY id")

def expenses_df():
    return qdf("SELECT * FROM expenses WHERE active=1 ORDER BY id")

def total_emi():
    d = loans_df()
    return float(d["emi"].sum()) if not d.empty else 0

def total_cards():
    d = cards_df()
    return float(d["balance"].sum()) if not d.empty else 0

def total_living():
    d = expenses_df()
    return float(d["planned"].sum()) if not d.empty else 0

def effective_foreclosure(row):
    return float(row["foreclosure_amount"]) + float(row["foreclosure_charge"])

def planned_foreclosures_df():
    return qdf("""
        SELECT f.id, f.loan_id, f.foreclosure_date, f.amount, f.charge, f.status,
               COALESCE(f.funded_by,'Friend') AS funded_by,
               l.name, l.emi, l.remaining_months
        FROM foreclosures f
        JOIN loans l ON l.id = f.loan_id
        WHERE f.status IN ('Planned', 'Paid')
        ORDER BY f.foreclosure_date DESC, f.id DESC
    """)

def foreclosed_loan_ids():
    if not get_setting_bool("friend_help_enabled", False):
        return set()
    d = planned_foreclosures_df()
    if d.empty:
        return set()
    return set(d["loan_id"].astype(int).tolist())

def scheduled_remaining(row):
    return float(row["emi"]) * int(row["remaining_months"])

def months_from(start, n):
    return pd.date_range(start=start, periods=n, freq="MS")

def forecast_df(months=24, salary_override=None):
    loans = loans_df()
    living = total_living()
    base_salary = float(get_setting("monthly_salary", 65000))
    future_salary = float(get_setting("future_salary", 75000))
    future_start = pd.to_datetime(get_setting("future_salary_start", "2026-11-01"))
    start = pd.to_datetime(get_setting("forecast_start", "2026-10-01"))
    closed_ids = foreclosed_loan_ids()

    rows = []
    for i, m in enumerate(months_from(start, months)):
        salary = base_salary if m < future_start else future_salary
        if salary_override is not None:
            salary = salary_override

        emi = 0
        detail = []
        for _, r in loans.iterrows():
            if int(r["id"]) in closed_ids:
                continue
            if int(r["remaining_months"]) > i:
                emi += float(r["emi"])
                detail.append((r["name"], float(r["emi"])))

        cash_flow = salary - living - emi
        rows.append({
            "Month": m.strftime("%b %Y"),
            "Salary": salary,
            "Living": living,
            "EMI": emi,
            "Cash Flow Before Friend": cash_flow,
            "Card Balance": total_cards(),
            "Loan EMI Count": len(detail),
        })
    return pd.DataFrame(rows)

# -----------------------------
# ⭐ Recommendation Engine
# -----------------------------
def _loan_candidates():
    """Build a scored DataFrame of every active loan with a foreclosure quote."""
    loans = loans_df().copy()
    loans = loans[loans["remaining_months"] > 0].copy()
    loans["Total Close"] = loans["foreclosure_amount"] + loans["foreclosure_charge"]
    loans["Scheduled Left"] = loans["emi"] * loans["remaining_months"]

    # A loan is "foreclosable" only if a quote exists
    loans["Foreclosable"] = loans["foreclosure_amount"] > 0

    # Financial metrics
    loans["Saving"] = loans["Scheduled Left"] - loans["Total Close"]  # +ve = saves money
    loans["EMI Freed"] = loans["emi"]
    loans["EMI per Lakh"] = loans.apply(
        lambda r: (r["EMI Freed"] / r["Total Close"] * 100000) if r["Total Close"] > 0 else 0,
        axis=1,
    )
    loans["Value Ratio"] = loans.apply(
        lambda r: (r["Saving"] / r["Total Close"]) if r["Total Close"] > 0 else 0,
        axis=1,
    )
    return loans

def suggest_best_foreclosure_package(budget=None):
    """
    Recommend which loans to foreclose using the friend money.

    Logic:
      1. Exclude loans with no foreclosure quote.
      2. Exclude loans where foreclosure costs MORE than remaining EMIs
         (negative saving) — these destroy value; flag them as Avoid.
      3. Rank the rest by EMI-freed-per-rupee (efficiency), tie-break by
         absolute EMI freed.
      4. Greedy knapsack: take highest-efficiency loans until budget runs out.
      5. Also score cards: clearing a card frees its minimum_due.

    Returns:
      must_close_df  — loans with saving > 0 and high efficiency
      avoid_df       — loans with negative saving (don't foreclose)
      all_ranked_df  — full ranked list of foreclosable loans
      recommended_df — the greedy package
      card_df        — cards with efficiency scoring
      totals         — dict of cost, emi_freed, saving
    """
    if budget is None:
        budget = float(get_setting("friend_balance", get_setting("friend_help_amount", 400000)))

    loans = _loan_candidates()

    # Cards
    cards = cards_df().copy()
    cards["Total Close"] = cards["balance"]
    cards["EMI Freed"] = cards["minimum_due"]
    cards["EMI per Lakh"] = cards.apply(
        lambda r: (r["EMI Freed"] / r["Total Close"] * 100000) if r["Total Close"] > 0 else 0,
        axis=1,
    )
    cards["Value Ratio"] = 0.0  # cards save nothing — you still owe the principal
    cards["Saving"] = -cards["balance"]  # closing a card is a pure cost, but stops interest
    cards["Scheduled Left"] = cards["balance"]

    foreclosable = loans[loans["Foreclosable"]].copy()

    if foreclosable.empty:
        empty = pd.DataFrame()
        return empty, empty, empty, empty, cards, {
            "cost": 0.0, "emi_freed": 0.0, "saving": 0.0, "card_cost": 0.0,
        }

    # Split into value-positive and value-negative
    avoid_df = foreclosable[foreclosable["Saving"] < 0].copy()
    positive = foreclosable[foreclosable["Saving"] >= 0].copy()

    # Rank positive loans by efficiency (EMI per Lakh), then by EMI freed
    positive = positive.sort_values(
        ["EMI per Lakh", "EMI Freed"], ascending=[False, False]
    ).reset_index(drop=True)

    # Greedy knapsack
    remaining = budget
    picked = []
    for _, r in positive.iterrows():
        cost = float(r["Total Close"])
        if cost <= remaining:
            picked.append(r)
            remaining -= cost

    recommended_df = pd.DataFrame(picked) if picked else pd.DataFrame()

    total_cost = float(recommended_df["Total Close"].sum()) if not recommended_df.empty else 0
    total_emi = float(recommended_df["EMI Freed"].sum()) if not recommended_df.empty else 0
    total_saving = float(recommended_df["Saving"].sum()) if not recommended_df.empty else 0

    return (
        positive,
        avoid_df,
        foreclosable.sort_values(["EMI per Lakh", "EMI Freed"], ascending=[False, False]),
        recommended_df,
        cards,
        {
            "cost": total_cost,
            "emi_freed": total_emi,
            "saving": total_saving,
            "card_cost": float(cards["Total Close"].sum()) if not cards.empty else 0.0,
            "budget": budget,
            "left": budget - total_cost,
        },
    )

def friend_plan(months=24):
    f = forecast_df(months)
    start_balance = float(get_setting("friend_balance", get_setting("friend_help_amount", 400000)))
    balance = start_balance

    repayments = []
    for i, (_, r) in enumerate(f.iterrows()):
        cf = float(r["Cash Flow Before Friend"])

        if i == 0 or balance <= 0 or cf <= 0:
            pay = 0
        else:
            if cf < 10000:
                pay = 10000
            elif cf < 20000:
                pay = 15000
            elif cf < 30000:
                pay = 25000
            elif cf < 40000:
                pay = 30000
            else:
                pay = 40000

            pay = min(pay, balance)
            pay = min(pay, max(0, cf))

        repayments.append(pay)
        balance -= pay

    f["Friend Repayment"] = repayments
    f["Cash Flow After Friend"] = f["Cash Flow Before Friend"] - f["Friend Repayment"]
    running = start_balance
    balances = []
    for pay in repayments:
        running = max(0, running - pay)
        balances.append(running)
    f["Friend Balance"] = balances
    return f

# -----------------------------
# Sidebar
# -----------------------------
st.sidebar.title("💰 Debt Command Center")

friend_on = get_setting_bool("friend_help_enabled", False)
if friend_on:
    st.sidebar.success("✅ Friend help: ON — foreclosures applied")
else:
    st.sidebar.info("ℹ️ Friend help: OFF — baseline EMI view")

page = st.sidebar.radio(
    "Go to",
    [
        "🏠 Command Center",
        "🎯 Recommendations",
        "📊 Forecast",
        "🏦 Loans & Foreclosures",
        "💳 Cards & CheQ",
        "🧾 Expenses",
        "🤝 Friend Loan",
        "⚙️ Settings",
    ],
)

# -----------------------------
# Command Center
# -----------------------------
if page == "🏠 Command Center":
    st.title("🏠 Debt-Free Command Center")
    st.caption("This app tells you what to do with your cash — not just record it.")

    salary = float(get_setting("monthly_salary", 65000))
    future_salary = float(get_setting("future_salary", 75000))
    living = total_living()
    emi = total_emi()
    planned = planned_foreclosures_df()

    if friend_on and not planned.empty:
        planned_emi = float(planned["emi"].sum())
    else:
        planned_emi = 0.0
    effective_current_emi = max(0, emi - planned_emi)

    cards = total_cards()
    friend_balance = float(get_setting("friend_balance", get_setting("friend_help_amount", 400000)))
    friend_used = float(get_setting("friend_amount_used", 0))
    pf = float(get_setting("pf_monthly", 1800))

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Current take-home", money(salary))
    c2.metric("Future target salary", money(future_salary))
    c3.metric("Active loan EMIs", money(effective_current_emi))
    c4.metric("Card balances", money(cards))

    if friend_on:
        st.success(
            f"✅ Friend help is **ON**. {money(planned_emi)}/month of EMIs are removed. "
            f"Friend balance: {money(friend_balance)}."
        )
    else:
        st.info(
            "ℹ️ Friend help is **OFF**. Forecast shows baseline EMI burden. "
            "Go to 🎯 Recommendations to see which loans to close."
        )

    # ⭐ Top-line recommendation
    st.divider()
    st.subheader("🎯 What should I do next?")
    pos, avoid, ranked, rec, cards_scored, totals = suggest_best_foreclosure_package()

    if rec.empty:
        st.warning("No foreclosure quotes entered yet — fill them in 🏦 Loans & Foreclosures.")
    else:
        r1, r2, r3, r4 = st.columns(4)
        r1.metric("Recommended package cost", money(totals["cost"]))
        r2.metric("EMI freed / month", money(totals["emi_freed"]))
        r3.metric("Net saving", money(totals["saving"]))
        r4.metric("Budget left", money(totals["left"]))

        st.write("**Close these loans first (highest EMI freed per rupee):**")
        st.dataframe(
            rec[["name", "emi", "remaining_months", "Total Close", "EMI Freed", "EMI per Lakh", "Saving"]]
            .rename(columns={
                "name": "Loan",
                "emi": "EMI",
                "remaining_months": "Months left",
                "Total Close": "Cost to close",
                "EMI Freed": "EMI freed",
                "EMI per Lakh": "EMI freed / ₹1L",
                "Saving": "Net saving",
            })
            .style.format({
                "EMI": "₹{:,.0f}",
                "Cost to close": "₹{:,.0f}",
                "EMI freed": "₹{:,.0f}",
                "EMI freed / ₹1L": "₹{:,.0f}",
                "Net saving": "₹{:,.0f}",
            }),
            use_container_width=True,
            hide_index=True,
        )

        st.info("Open **🎯 Recommendations** for the full analysis, ranking and one-click apply.")

    st.divider()
    st.subheader("1. Your current monthly position")
    if friend_on and not planned.empty:
        st.success(
            f"Forecast is applying {len(planned)} planned foreclosure(s), "
            f"freeing {money(planned_emi)}/month."
        )
    a, b, c, d = st.columns(4)
    a.metric("Living costs", money(living))
    b.metric("Loan EMIs", money(effective_current_emi))
    c.metric("Cash flow before friend", money(salary - living - effective_current_emi))
    d.metric("PF added monthly", money(pf))

    current_cf = salary - living - effective_current_emi
    if current_cf < 0:
        st.error(f"⚠️ You are short by {money(abs(current_cf))} before any friend repayment.")
    else:
        st.success(f"Monthly cash flow is positive by {money(current_cf)} before friend repayment.")

    st.subheader("2. Card rotation warning")
    rotations = qdf("""
        SELECT COUNT(*) AS cnt, COALESCE(SUM(fee),0) AS fees
        FROM card_rotations
        WHERE rotation_date >= date('now','-30 day')
    """)
    recent_fees = float(rotations.iloc[0]["fees"]) if not rotations.empty else 0
    if cards > 0:
        st.warning(
            f"💳 Cards still carry about {money(cards)}. "
            f"Recent logged CheQ fees: {money(recent_fees)}."
        )
    else:
        st.success("Cards are currently at ₹0. Keep them from rebuilding.")

    st.subheader("3. Friend-loan step-up plan")
    fp = friend_plan(18)
    first_zero = fp[fp["Friend Balance"] <= 0]
    if not first_zero.empty:
        payoff_month = first_zero.iloc[0]["Month"]
        st.success(f"Friend balance is projected to finish by {payoff_month}.")
    else:
        st.info("Step-up rules do not fully repay the friend within the displayed horizon.")

    st.dataframe(
        fp[["Month", "Salary", "EMI", "Cash Flow Before Friend",
            "Friend Repayment", "Cash Flow After Friend", "Friend Balance"]]
        .head(12)
        .rename(columns={
            "Cash Flow Before Friend": "Before Friend",
            "Friend Repayment": "Friend Payment",
            "Cash Flow After Friend": "After Friend",
        })
        .style.format({
            "Salary": "₹{:,.0f}",
            "EMI": "₹{:,.0f}",
            "Before Friend": "₹{:,.0f}",
            "Friend Payment": "₹{:,.0f}",
            "After Friend": "₹{:,.0f}",
            "Friend Balance": "₹{:,.0f}",
        }),
        use_container_width=True,
        hide_index=True,
    )

# -----------------------------
# ⭐ Recommendations page
# -----------------------------
elif page == "🎯 Recommendations":
    st.title("🎯 Which loans should I close?")
    st.caption(
        "The engine ranks every loan by **EMI freed per ₹1L spent** "
        "and warns you when foreclosing costs more than the remaining EMIs."
    )

    friend_cash = float(get_setting("friend_balance", get_setting("friend_help_amount", 400000)))
    budget = st.number_input(
        "How much friend cash do you want to deploy?",
        min_value=0.0,
        value=friend_cash,
        step=5000.0,
    )

    pos, avoid, ranked, rec, cards_scored, totals = suggest_best_foreclosure_package(budget)

    # --- Summary ---
    s1, s2, s3, s4 = st.columns(4)
    s1.metric("Budget", money(totals.get("budget", budget)))
    s2.metric("Recommended cost", money(totals["cost"]))
    s3.metric("EMI freed / month", money(totals["emi_freed"]))
    s4.metric("Budget left", money(totals["left"]))

    st.divider()

    # --- Recommended package ---
    st.subheader("✅ Recommended package (greedy by value)")
    if rec.empty:
        st.warning(
            "No loans fit within this budget with a positive saving. "
            "Either increase the budget or check the Avoid list below."
        )
    else:
        st.success(
            f"Close **{len(rec)}** loan(s) for **{money(totals['cost'])}**, "
            f"freeing **{money(totals['emi_freed'])}/month**, "
            f"net saving **{money(totals['saving'])}**."
        )
        st.dataframe(
            rec[["name", "emi", "remaining_months", "Total Close",
                 "Scheduled Left", "Saving", "EMI Freed", "EMI per Lakh", "notes"]]
            .rename(columns={
                "name": "Loan",
                "emi": "EMI",
                "remaining_months": "Months left",
                "Total Close": "Cost to close",
                "Scheduled Left": "Scheduled EMIs left",
                "Saving": "Net saving",
                "EMI Freed": "EMI freed",
                "EMI per Lakh": "EMI freed / ₹1L",
                "notes": "Notes",
            })
            .style.format({
                "EMI": "₹{:,.0f}",
                "Cost to close": "₹{:,.0f}",
                "Scheduled EMIs left": "₹{:,.0f}",
                "Net saving": "₹{:,.0f}",
                "EMI freed": "₹{:,.0f}",
                "EMI freed / ₹1L": "₹{:,.0f}",
            }),
            use_container_width=True,
            hide_index=True,
        )

    # --- Avoid list ---
    st.divider()
    st.subheader("🚫 Do NOT foreclose these")
    if avoid.empty:
        st.success("No value-destroying loans found — every foreclosure quote beats the remaining EMIs.")
    else:
        st.error(
            "For these loans, the foreclosure quote is **higher** than the EMIs you'd "
            "still pay. Closing them costs you extra money. Just keep paying the EMI."
        )
        st.dataframe(
            avoid[["name", "emi", "remaining_months", "Total Close",
                   "Scheduled Left", "Saving", "notes"]]
            .rename(columns={
                "name": "Loan",
                "emi": "EMI",
                "remaining_months": "Months left",
                "Total Close": "Cost to close",
                "Scheduled Left": "Scheduled EMIs left",
                "Saving": "Net saving (negative = worse)",
                "notes": "Notes",
            })
            .style.format({
                "EMI": "₹{:,.0f}",
                "Cost to close": "₹{:,.0f}",
                "Scheduled EMIs left": "₹{:,.0f}",
                "Net saving (negative = worse)": "₹{:,.0f}",
            }),
            use_container_width=True,
            hide_index=True,
        )

    # --- Full ranking ---
    st.divider()
    st.subheader("📋 Full ranking (every foreclosable loan)")
    if ranked.empty:
        st.info("No foreclosable loans found.")
    else:
        st.dataframe(
            ranked[["name", "emi", "remaining_months", "Total Close",
                    "Scheduled Left", "Saving", "EMI Freed", "EMI per Lakh", "notes"]]
            .rename(columns={
                "name": "Loan",
                "emi": "EMI",
                "remaining_months": "Months left",
                "Total Close": "Cost to close",
                "Scheduled Left": "Scheduled EMIs left",
                "Saving": "Net saving",
                "EMI Freed": "EMI freed",
                "EMI per Lakh": "EMI freed / ₹1L",
                "notes": "Notes",
            })
            .style.format({
                "EMI": "₹{:,.0f}",
                "Cost to close": "₹{:,.0f}",
                "Scheduled EMIs left": "₹{:,.0f}",
                "Net saving": "₹{:,.0f}",
                "EMI freed": "₹{:,.0f}",
                "EMI freed / ₹1L": "₹{:,.0f}",
            }),
            use_container_width=True,
            hide_index=True,
        )

    # --- Cards scoring ---
    st.divider()
    st.subheader("💳 Cards — value of clearing")
    st.caption(
        "Cards don't save you principal (you still owe the balance). "
        "But clearing them stops interest and frees the minimum due. "
        "Ranked by **minimum due freed per ₹1L cleared**."
    )
    if cards_scored.empty:
        st.info("No active cards.")
    else:
        st.dataframe(
            cards_scored[["name", "balance", "minimum_due", "EMI per Lakh"]]
            .rename(columns={
                "name": "Card",
                "balance": "Balance to clear",
                "minimum_due": "Minimum due freed",
                "EMI per Lakh": "Min due freed / ₹1L",
            })
            .style.format({
                "Balance to clear": "₹{:,.0f}",
                "Minimum due freed": "₹{:,.0f}",
                "Min due freed / ₹1L": "₹{:,.0f}",
            }),
            use_container_width=True,
            hide_index=True,
        )

    # --- Apply ---
    st.divider()
    st.subheader("Apply the recommended package")
    st.caption(
        "This will mark the recommended loans as Planned foreclosures, "
        "clear the cards if you tick the box, and turn Friend Help ON."
    )

    clear_cards_too = st.checkbox(
        f"Also clear all card balances ({money(totals['card_cost'])})",
        value=True,
    )

    total_use = totals["cost"] + (totals["card_cost"] if clear_cards_too else 0)
    if total_use > budget:
        st.error(
            f"❌ Package + cards = {money(total_use)}, exceeds your {money(budget)} budget. "
            "Uncheck cards or raise the budget."
        )
        apply_disabled = True
    else:
        st.success(
            f"✅ Total use: {money(total_use)} — leaves {money(budget - total_use)} of friend cash."
        )
        apply_disabled = rec.empty

    if st.button("🚀 Apply recommended package", type="primary", disabled=apply_disabled):
        conn = db()
        forecast_date = pd.to_datetime(
            get_setting("forecast_start", "2026-10-01")
        ).date().isoformat()

        conn.execute("DELETE FROM foreclosures WHERE status='Planned'")

        for _, r in rec.iterrows():
            conn.execute("""
                INSERT INTO foreclosures
                (loan_id, foreclosure_date, amount, charge, status, funded_by)
                VALUES (?,?,?,?,?,?)
            """, (
                int(r["id"]),
                forecast_date,
                float(r["foreclosure_amount"]),
                float(r["foreclosure_charge"]),
                "Planned",
                "Friend",
            ))

        if clear_cards_too:
            conn.execute("UPDATE cards SET balance=0, minimum_due=0 WHERE active=1")

        conn.commit()
        conn.close()

        new_used = float(get_setting("friend_amount_used", 0)) + total_use
        agreed = float(get_setting("friend_help_amount", 400000))
        new_balance = max(0.0, agreed - new_used)

        set_setting("friend_amount_used", new_used)
        set_setting("friend_balance", new_balance)
        set_setting("friend_help_enabled", "1")

        st.success(f"Applied. Friend help ON. Outstanding to friend: {money(new_balance)}.")
        st.rerun()

# -----------------------------
# Forecast
# -----------------------------
elif page == "📊 Forecast":
    st.title("📊 24-Month Cashflow Forecast")

    if friend_on:
        st.success("✅ Showing forecast **with** friend help applied.")
    else:
        st.info("ℹ️ Showing forecast **without** friend help (baseline EMI). Enable in 🎯 Recommendations or 🤝 Friend Loan.")

    f = friend_plan(24)
    st.dataframe(
        f.style.format({
            "Salary": "₹{:,.0f}",
            "Living": "₹{:,.0f}",
            "EMI": "₹{:,.0f}",
            "Cash Flow Before Friend": "₹{:,.0f}",
            "Friend Repayment": "₹{:,.0f}",
            "Cash Flow After Friend": "₹{:,.0f}",
            "Card Balance": "₹{:,.0f}",
            "Friend Balance": "₹{:,.0f}",
        }),
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("Cash flow")
    chart_df = f.set_index("Month")[["Cash Flow Before Friend", "Cash Flow After Friend"]]
    st.line_chart(chart_df)

    st.subheader("Friend balance")
    st.line_chart(f.set_index("Month")[["Friend Balance"]])

# -----------------------------
# Loans & Foreclosures
# -----------------------------
elif page == "🏦 Loans & Foreclosures":
    st.title("🏦 Loans & Foreclosures")

    st.subheader("Loan table")
    loans = loans_df()
    if not loans.empty:
        view = loans.copy()
        view["Effective Foreclosure"] = view["foreclosure_amount"] + view["foreclosure_charge"]
        view["Scheduled Remaining"] = view["emi"] * view["remaining_months"]
        view["Saving / (Extra Cost)"] = view["Scheduled Remaining"] - view["Effective Foreclosure"]
        view["EMI Freed"] = view["emi"]

        st.dataframe(
            view[
                ["name", "emi", "remaining_months", "emi_day",
                 "foreclosure_amount", "foreclosure_charge",
                 "Effective Foreclosure", "Scheduled Remaining",
                 "Saving / (Extra Cost)", "EMI Freed", "notes"]
            ].rename(columns={
                "name": "Loan",
                "emi": "EMI",
                "remaining_months": "Months left",
                "emi_day": "EMI day",
                "foreclosure_amount": "Quoted foreclosure",
                "foreclosure_charge": "Charges",
                "Effective Foreclosure": "Total to close",
                "Scheduled Remaining": "Scheduled EMIs left",
                "Saving / (Extra Cost)": "Saving / extra cost",
                "EMI Freed": "Monthly EMI freed",
                "notes": "Notes",
            }).style.format({
                "EMI": "₹{:,.0f}",
                "Quoted foreclosure": "₹{:,.0f}",
                "Charges": "₹{:,.0f}",
                "Total to close": "₹{:,.0f}",
                "Scheduled EMIs left": "₹{:,.0f}",
                "Saving / extra cost": "₹{:,.0f}",
                "Monthly EMI freed": "₹{:,.0f}",
            }),
            use_container_width=True,
            hide_index=True,
        )

    st.divider()
    st.subheader("Edit loan / foreclosure quote")

    names = loans["name"].tolist() if not loans.empty else []
    if names:
        selected = st.selectbox("Loan", names)
        row = loans[loans["name"] == selected].iloc[0]

        with st.form("loan_edit"):
            emi = st.number_input("Monthly EMI", value=float(row["emi"]), step=100.0)
            months = st.number_input("Remaining months", value=int(row["remaining_months"]), min_value=0, step=1)
            emi_day = st.number_input("EMI day", value=int(row["emi_day"]), min_value=1, max_value=31, step=1)
            foreclosure = st.number_input(
                "Foreclosure amount",
                value=float(row["foreclosure_amount"]),
                min_value=0.0,
                step=100.0,
            )
            charge = st.number_input(
                "Foreclosure charges",
                value=float(row["foreclosure_charge"]),
                min_value=0.0,
                step=50.0,
            )
            notes = st.text_input("Notes", value=str(row["notes"] or ""))
            save = st.form_submit_button("Save loan")

        if save:
            conn = db()
            conn.execute("""
                UPDATE loans
                SET emi=?, remaining_months=?, emi_day=?,
                    foreclosure_amount=?, foreclosure_charge=?, notes=?
                WHERE name=?
            """, (emi, months, emi_day, foreclosure, charge, notes, selected))
            conn.commit()
            conn.close()
            st.success("Loan updated.")
            st.rerun()

# -----------------------------
# Cards & CheQ
# -----------------------------
elif page == "💳 Cards & CheQ":
    st.title("💳 Cards & CheQ")

    cards = cards_df()
    total = float(cards["balance"].sum()) if not cards.empty else 0

    c1, c2, c3 = st.columns(3)
    c1.metric("Total card balance", money(total))
    c2.metric("Cards", len(cards))
    c3.metric("CheQ fee / card", money(float(get_setting("cheq_fee_per_card", 2000))))

    st.dataframe(
        cards.rename(columns={
            "name": "Card",
            "balance": "Balance",
            "minimum_due": "Minimum due",
            "due_day": "Due day",
        })[["Card", "Balance", "Minimum due", "Due day"]].style.format({
            "Balance": "₹{:,.0f}",
            "Minimum due": "₹{:,.0f}",
        }),
        use_container_width=True,
        hide_index=True,
    )

    st.divider()
    st.subheader("Update card balance")

    if not cards.empty:
        card_name = st.selectbox("Card", cards["name"].tolist())
        r = cards[cards["name"] == card_name].iloc[0]
        with st.form("card_edit"):
            balance = st.number_input("Current balance", value=float(r["balance"]), step=500.0)
            minimum = st.number_input("Minimum due", value=float(r["minimum_due"]), step=100.0)
            due = st.number_input("Due day", value=int(r["due_day"]), min_value=1, max_value=31)
            save = st.form_submit_button("Save card")
        if save:
            conn = db()
            conn.execute(
                "UPDATE cards SET balance=?, minimum_due=?, due_day=? WHERE name=?",
                (balance, minimum, due, card_name)
            )
            conn.commit()
            conn.close()
            st.success("Card updated.")
            st.rerun()

    st.divider()
    st.subheader("Log a CheQ rotation")
    st.warning(
        "A CheQ rotation is treated as recycling debt, not as income. "
        "The fee is a real expense."
    )

    if not cards.empty:
        with st.form("rotation"):
            rdate = st.date_input("Rotation date", value=date.today())
            card_name = st.selectbox("Card to rotate", cards["name"].tolist())
            amount = st.number_input("Amount recycled", min_value=0.0, step=500.0)
            fee = st.number_input(
                "CheQ fee",
                value=float(get_setting("cheq_fee_per_card", 2000)),
                min_value=0.0,
                step=100.0,
            )
            notes = st.text_input("Notes")
            save = st.form_submit_button("Log rotation")

        if save and amount > 0:
            card_id = int(cards[cards["name"] == card_name].iloc[0]["id"])
            conn = db()
            conn.execute("""
                INSERT INTO card_rotations(rotation_date,card_id,amount,fee,notes)
                VALUES(?,?,?,?,?)
            """, (str(rdate), card_id, amount, fee, notes))
            conn.commit()
            conn.close()
            st.success("Rotation logged.")
            st.rerun()

    st.subheader("Recent rotations")
    rot = qdf("""
        SELECT r.rotation_date, c.name AS card, r.amount, r.fee, r.notes
        FROM card_rotations r
        JOIN cards c ON c.id=r.card_id
        ORDER BY r.rotation_date DESC, r.id DESC
        LIMIT 30
    """)
    if not rot.empty:
        st.dataframe(
            rot.rename(columns={
                "rotation_date": "Date",
                "card": "Card",
                "amount": "Recycled amount",
                "fee": "Fee",
                "notes": "Notes",
            }).style.format({
                "Recycled amount": "₹{:,.0f}",
                "Fee": "₹{:,.0f}",
            }),
            use_container_width=True,
            hide_index=True,
        )

# -----------------------------
# Expenses
# -----------------------------
elif page == "🧾 Expenses":
    st.title("🧾 Expense Manager")

    exp = expenses_df()
    st.metric("Planned living costs / month", money(total_living()))

    st.dataframe(
        exp.rename(columns={
            "category": "Category",
            "planned": "Planned / month",
        })[["Category", "Planned / month"]].style.format({
            "Planned / month": "₹{:,.0f}",
        }),
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("Edit monthly expense")
    if not exp.empty:
        cat = st.selectbox("Category", exp["category"].tolist())
        r = exp[exp["category"] == cat].iloc[0]
        with st.form("expense_edit"):
            amount = st.number_input(
                "Planned monthly amount",
                value=float(r["planned"]),
                min_value=0.0,
                step=100.0,
            )
            save = st.form_submit_button("Save expense")
        if save:
            conn = db()
            conn.execute("UPDATE expenses SET planned=? WHERE category=?", (amount, cat))
            conn.commit()
            conn.close()
            st.success("Expense updated.")
            st.rerun()

# -----------------------------
# Friend Loan
# -----------------------------
elif page == "🤝 Friend Loan":
    st.title("🤝 Friend Loan — Withdrawal & Step-Up Manager")

    amount = float(get_setting("friend_help_amount", 400000))
    balance = float(get_setting("friend_balance", amount))
    used = float(get_setting("friend_amount_used", 0))
    target = get_setting("friend_target_date", "2028-03-31")
    enabled = get_setting_bool("friend_help_enabled", False)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Agreed friend help", money(amount))
    c2.metric("Already withdrawn", money(used))
    c3.metric("Outstanding to friend", money(balance))
    c4.metric("Target date", target)

    if enabled:
        st.success("✅ Friend help is currently **ON** — foreclosures are applied.")
    else:
        st.warning("⚠️ Friend help is **OFF** — forecast shows baseline EMI.")

    st.info(
        "Want a shortcut? Go to **🎯 Recommendations** — the engine will pick the "
        "best loan package for you automatically."
    )

    st.divider()
    st.subheader("Manual draw & apply")

    available_to_draw = max(0.0, amount - used)
    draw_amount = st.number_input(
        "Amount to draw from friend",
        min_value=0.0,
        max_value=float(available_to_draw),
        value=float(min(available_to_draw, 400000)),
        step=5000.0,
    )

    loans = loans_df()
    closable = loans[(loans["foreclosure_amount"] > 0) & (loans["remaining_months"] > 0)].copy()
    closable["Total Close"] = closable["foreclosure_amount"] + closable["foreclosure_charge"]

    if not closable.empty:
        # Pre-select based on recommendation engine
        _, _, _, rec, _, _ = suggest_best_foreclosure_package(draw_amount)
        default_sel = rec["name"].tolist() if not rec.empty else []

        selected_loans = st.multiselect(
            "Loans to foreclose with friend money",
            options=closable["name"].tolist(),
            default=default_sel,
        )
        chosen = closable[closable["name"].isin(selected_loans)]
        loan_cost = float(chosen["Total Close"].sum()) if not chosen.empty else 0.0
        emi_freed = float(chosen["emi"].sum()) if not chosen.empty else 0.0

        cards = cards_df()
        total_card_bal = float(cards["balance"].sum()) if not cards.empty else 0
        clear_cards = st.checkbox(
            f"Clear all card balances ({money(total_card_bal)})",
            value=(total_card_bal > 0),
        )
        card_cost = total_card_bal if clear_cards else 0.0

        total_use = loan_cost + card_cost

        s1, s2, s3, s4 = st.columns(4)
        s1.metric("Draw amount", money(draw_amount))
        s2.metric("Loans to close", money(loan_cost))
        s3.metric("Cards to clear", money(card_cost))
        s4.metric("Left un-used", money(max(0, draw_amount - total_use)))

        if total_use > draw_amount:
            st.error(f"❌ Package costs {money(total_use)}, draw is {money(draw_amount)}.")
        else:
            st.success(
                f"✅ Draw covers package. Frees {money(emi_freed)}/month."
            )

        apply = st.button(
            "🚀 Apply draw & foreclosures",
            type="primary",
            disabled=(total_use > draw_amount or total_use <= 0),
        )

        if apply:
            conn = db()
            forecast_date = pd.to_datetime(
                get_setting("forecast_start", "2026-10-01")
            ).date().isoformat()
            conn.execute("DELETE FROM foreclosures WHERE status='Planned'")
            for _, r in chosen.iterrows():
                conn.execute("""
                    INSERT INTO foreclosures
                    (loan_id, foreclosure_date, amount, charge, status, funded_by)
                    VALUES (?,?,?,?,?,?)
                """, (
                    int(r["id"]), forecast_date,
                    float(r["foreclosure_amount"]),
                    float(r["foreclosure_charge"]),
                    "Planned", "Friend",
                ))
            if clear_cards:
                conn.execute("UPDATE cards SET balance=0, minimum_due=0 WHERE active=1")
            conn.commit()
            conn.close()

            new_used = used + total_use
            new_balance = max(0.0, amount - new_used)
            set_setting("friend_amount_used", new_used)
            set_setting("friend_balance", new_balance)
            set_setting("friend_help_enabled", "1")
            st.success("Applied.")
            st.rerun()

    if used > 0 or enabled:
        st.divider()
        if st.button("🔁 Reset friend help"):
            conn = db()
            conn.execute("DELETE FROM foreclosures WHERE status='Planned'")
            conn.commit()
            conn.close()
            set_setting("friend_amount_used", 0)
            set_setting("friend_balance", amount)
            set_setting("friend_help_enabled", "0")
            st.success("Reset.")
            st.rerun()

    st.divider()
    st.subheader("Projected step-up schedule")
    fp = friend_plan(24)
    st.dataframe(
        fp[["Month", "Salary", "EMI", "Cash Flow Before Friend",
            "Friend Repayment", "Cash Flow After Friend", "Friend Balance"]]
        .style.format({
            "Salary": "₹{:,.0f}",
            "EMI": "₹{:,.0f}",
            "Cash Flow Before Friend": "₹{:,.0f}",
            "Friend Repayment": "₹{:,.0f}",
            "Cash Flow After Friend": "₹{:,.0f}",
            "Friend Balance": "₹{:,.0f}",
        }),
        use_container_width=True,
        hide_index=True,
    )

# -----------------------------
# Settings
# -----------------------------
elif page == "⚙️ Settings":
    st.title("⚙️ Settings")

    with st.form("settings_form"):
        salary = st.number_input(
            "Current monthly take-home salary",
            value=float(get_setting("monthly_salary", 65000)),
            step=1000.0,
        )
        future_salary = st.number_input(
            "Expected salary after job change",
            value=float(get_setting("future_salary", 75000)),
            step=1000.0,
        )
        future_start = st.date_input(
            "Expected job-change salary start",
            value=pd.to_datetime(get_setting("future_salary_start", "2026-11-01")).date(),
        )
        pf = st.number_input(
            "PF added each month",
            value=float(get_setting("pf_monthly", 1800)),
            min_value=0.0, step=100.0,
        )
        cash = st.number_input(
            "Starting / available cash",
            value=float(get_setting("starting_cash", 20000)),
            min_value=0.0, step=1000.0,
        )
        forecast_start = st.date_input(
            "Forecast start month",
            value=pd.to_datetime(get_setting("forecast_start", "2026-10-01")).date(),
        )
        cheq = st.number_input(
            "CheQ fee per rotated card",
            value=float(get_setting("cheq_fee_per_card", 2000)),
            min_value=0.0, step=100.0,
        )
        save = st.form_submit_button("Save settings")

    if save:
        set_setting("monthly_salary", salary)
        set_setting("future_salary", future_salary)
        set_setting("future_salary_start", future_start.isoformat())
        set_setting("pf_monthly", pf)
        set_setting("starting_cash", cash)
        set_setting("forecast_start", forecast_start.isoformat())
        set_setting("cheq_fee_per_card", cheq)
        st.success("Settings saved.")
        st.rerun()

    st.divider()
    st.subheader("Friend help master switch")
    friend_on_now = get_setting_bool("friend_help_enabled", False)
    new_state = st.toggle(
        "Enable friend help in forecast",
        value=friend_on_now,
    )
    if new_state != friend_on_now:
        set_setting("friend_help_enabled", "1" if new_state else "0")
        st.rerun()

    st.divider()
    st.subheader("Current setup summary")
    st.write({
        "Salary now": money(float(get_setting("monthly_salary"))),
        "Expected salary": money(float(get_setting("future_salary"))),
        "Friend help agreed": money(float(get_setting("friend_help_amount"))),
        "Friend withdrawn": money(float(get_setting("friend_amount_used", 0))),
        "Friend outstanding": money(float(get_setting("friend_balance"))),
        "Friend help enabled": "ON" if get_setting_bool("friend_help_enabled") else "OFF",
        "Living expenses": money(total_living()),
        "Loan EMI (raw)": money(total_emi()),
        "Card balance": money(total_cards()),
    })
