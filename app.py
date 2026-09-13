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

    # Migrate: add funded_by if missing on existing DB
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
    """
    Return loan IDs to treat as closed in the forecast.
    If friend_help_enabled is OFF, we still want to show the BASELINE EMI burden,
    so we return an empty set (no loan is considered 'closed' for EMI purposes).
    """
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

def loan_emi_for_months(loans, month_index):
    total = 0
    details = []
    for _, r in loans.iterrows():
        if int(r["remaining_months"]) > month_index:
            total += float(r["emi"])
            details.append((r["name"], float(r["emi"])))
    return total, details

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

def recommended_friend_plan():
    loans = loans_df()
    names = ["Flexipay", "Stashfin", "Instamoney"]
    selected = loans[loans["name"].isin(names)].copy()
    selected["Total Close"] = selected["foreclosure_amount"] + selected["foreclosure_charge"]
    cost = float(selected["Total Close"].sum()) if not selected.empty else 0
    emi_freed = float(selected["emi"].sum()) if not selected.empty else 0
    cards = total_cards()
    total_use = cost + cards
    friend_cash = float(get_setting("friend_balance", get_setting("friend_help_amount", 400000)))
    return selected, cost, emi_freed, cards, total_use, friend_cash


def friend_plan(months=24):
    """
    Build a step-up repayment schedule.
    Repayment never pushes Cash Flow After Friend below zero.
    Uses friend_balance as the starting outstanding.
    """
    f = forecast_df(months)
    start_balance = float(get_setting("friend_balance", get_setting("friend_help_amount", 400000)))
    balance = start_balance

    repayments = []
    for i, (_, r) in enumerate(f.iterrows()):
        cf = float(r["Cash Flow Before Friend"])

        # Skip month 0 (start month) — no repayment the month you start
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

    # Effective EMI depends on whether friend help is enabled
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
            f"✅ Friend help is **ON**. {money(planned_emi)}/month of EMIs are removed "
            f"from the forecast. Friend balance: {money(friend_balance)}."
        )
    else:
        st.info(
            "ℹ️ Friend help is **OFF**. The forecast below shows your **baseline EMI burden**. "
            "Go to 🤝 Friend Loan to draw an amount and enable the plan."
        )

    st.divider()

    st.subheader("🎯 Recommended ₹4L debt-restructuring scenario")
    rec, rec_loan_cost, rec_emi_freed, rec_card_cost, rec_total_use, rec_friend_cash = recommended_friend_plan()
    rec_left = rec_friend_cash - rec_total_use

    rc1, rc2, rc3 = st.columns(3)
    rc1.metric("Recommended debt cleared", money(rec_total_use))
    rc2.metric("EMI freed", money(rec_emi_freed))
    rc3.metric("Friend cash left", money(max(0, rec_left)))

    st.caption(
        "Default scenario: Flexipay + Stashfin + Instamoney + clear the 3 cards. "
        "You can change the foreclosure quotes or friend amount before applying."
    )

    if st.button("🚀 APPLY RECOMMENDED SCENARIO", type="primary"):
        conn = db()
        forecast_date = pd.to_datetime(
            get_setting("forecast_start", "2026-10-01")
        ).date().isoformat()

        for _, r in rec.iterrows():
            exists = conn.execute(
                "SELECT 1 FROM foreclosures WHERE loan_id=? AND status IN ('Planned','Paid') LIMIT 1",
                (int(r["id"]),)
            ).fetchone()
            if not exists:
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

        conn.execute("UPDATE cards SET balance=0, minimum_due=0 WHERE active=1")
        conn.commit()
        conn.close()

        # Consume the recommended total from friend balance, enable friend help
        used_now = rec_total_use
        new_balance = max(0, rec_friend_cash - used_now)
        set_setting("friend_amount_used", float(get_setting("friend_amount_used", 0)) + used_now)
        set_setting("friend_balance", new_balance)
        set_setting("friend_help_enabled", "1")

        st.success(
            "Scenario applied. Friend help is now ON, EMIs removed, cards cleared."
        )
        st.rerun()

    # Current cashflow — uses effective EMI
    current_cf = salary - living - effective_current_emi
    st.subheader("1. Your current monthly position")
    if friend_on and not planned.empty:
        st.success(
            f"Forecast is applying {len(planned)} planned foreclosure(s), "
            f"freeing {money(planned_emi)}/month."
        )
    a, b, c, d = st.columns(4)
    a.metric("Living costs", money(living))
    b.metric("Loan EMIs", money(effective_current_emi))
    c.metric("Cash flow before friend", money(current_cf))
    d.metric("PF added monthly", money(pf))

    if current_cf < 0:
        st.error(
            f"⚠️ You are short by {money(abs(current_cf))} before any friend repayment."
        )
    else:
        st.success(f"Monthly cash flow is positive by {money(current_cf)} before friend repayment.")

    st.subheader("2. Recommended debt actions")
    loans = loans_df().copy()
    loans["Effective Foreclosure"] = loans["foreclosure_amount"] + loans["foreclosure_charge"]
    loans["Scheduled Remaining"] = loans["emi"] * loans["remaining_months"]
    loans["Saving / (Extra Cost)"] = loans["Scheduled Remaining"] - loans["Effective Foreclosure"]
    loans["EMI Freed"] = loans["emi"]

    candidates = loans[
        (loans["Effective Foreclosure"] > 0) &
        (loans["remaining_months"] > 0)
    ].copy()

    if not candidates.empty:
        candidates["Value"] = candidates["Saving / (Extra Cost)"] / candidates["Effective Foreclosure"]
        recommended = candidates.sort_values(
            ["Saving / (Extra Cost)", "EMI Freed"],
            ascending=[False, False]
        ).head(5)

        st.dataframe(
            recommended[
                ["name", "emi", "remaining_months", "Effective Foreclosure",
                 "Scheduled Remaining", "Saving / (Extra Cost)", "EMI Freed", "notes"]
            ].rename(columns={
                "name": "Loan",
                "emi": "EMI",
                "remaining_months": "Months left",
                "Effective Foreclosure": "Foreclosure incl. charges",
                "Scheduled Remaining": "Remaining scheduled EMIs",
                "Saving / (Extra Cost)": "Economic saving / cost",
                "EMI Freed": "EMI freed",
                "notes": "Notes",
            }),
            use_container_width=True,
            hide_index=True,
        )

    st.info(
        "Planning rule: during negative cash-flow months, protect the bridge reserve. "
        "Once cash flow turns positive, redirect every freed EMI toward the next debt target."
    )

    st.subheader("3. Card rotation warning")
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
        st.success("Cards are currently at ₹0 in the tracker. Keep them from rebuilding.")

    st.subheader("4. Friend-loan step-up plan")
    fp = friend_plan(18)
    first_zero = fp[fp["Friend Balance"] <= 0]
    if not first_zero.empty:
        payoff_month = first_zero.iloc[0]["Month"]
        st.success(f"At the current step-up rules, the friend balance is projected to finish by {payoff_month}.")
    else:
        st.info("The current step-up rules do not fully repay the friend within the displayed horizon.")

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

    st.subheader("5. Your decision rule")
    st.markdown("""
    **If cash flow is negative → preserve cash and avoid new borrowing.**

    **If cash flow is positive but below ₹10k → friend payment stays small.**

    **When an EMI disappears → increase friend repayment by the amount of the freed EMI.**

    **When salary increases → increase friend repayment instead of increasing lifestyle spending.**

    **When cards are cleared → stop routine CheQ rotation.**

    **PF ₹1,800/month → treat as long-term savings, not monthly spending money.**
    """)

# -----------------------------
# Forecast
# -----------------------------
elif page == "📊 Forecast":
    st.title("📊 24-Month Cashflow Forecast")

    if friend_on:
        st.success("✅ Showing forecast **with** friend help applied.")
    else:
        st.info("ℹ️ Showing forecast **without** friend help (baseline EMI burden). Enable it in 🤝 Friend Loan.")

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

    st.caption(
        "Toggle friend help in 🤝 Friend Loan to switch between baseline EMI and post-foreclosure EMI."
    )

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

    st.divider()
    st.subheader("Foreclosure planner")
    st.caption("Actual foreclosure quote is used — not EMI × remaining months.")

    loans = loans_df()
    if not loans.empty:
        planner = loans[loans["foreclosure_amount"] > 0].copy()
        planner["Total Close"] = planner["foreclosure_amount"] + planner["foreclosure_charge"]
        planner["Scheduled"] = planner["emi"] * planner["remaining_months"]
        planner["Saving"] = planner["Scheduled"] - planner["Total Close"]
        planner["EMI Freed"] = planner["emi"]
        planner["EMI freed / ₹1L"] = planner["EMI Freed"] / planner["Total Close"] * 100000

        st.dataframe(
            planner[
                ["name", "Total Close", "Saving", "EMI Freed", "EMI freed / ₹1L", "notes"]
            ].rename(columns={
                "name": "Loan",
                "Total Close": "Cost to close",
                "Saving": "Saving / extra cost",
                "EMI Freed": "EMI freed",
                "EMI freed / ₹1L": "EMI freed per ₹1L",
                "notes": "Notes",
            }).style.format({
                "Cost to close": "₹{:,.0f}",
                "Saving / extra cost": "₹{:,.0f}",
                "EMI freed": "₹{:,.0f}",
                "EMI freed per ₹1L": "₹{:,.0f}",
            }),
            use_container_width=True,
            hide_index=True,
        )

        st.write("### Test a foreclosure budget")
        budget = st.number_input("Available foreclosure budget", value=400000.0, step=5000.0)
        remaining_budget = budget
        selected_rows = []
        for _, r in planner.sort_values(
            ["Saving", "EMI Freed"], ascending=[False, False]
        ).iterrows():
            cost = float(r["Total Close"])
            if cost <= remaining_budget:
                selected_rows.append(r)
                remaining_budget -= cost

        if selected_rows:
            s = pd.DataFrame(selected_rows)
            st.success(
                f"Simple value-first selection uses {money(budget-remaining_budget)} "
                f"and leaves {money(remaining_budget)}."
            )
            st.dataframe(
                s[["name", "Total Close", "Saving", "EMI Freed"]].rename(columns={
                    "name": "Loan",
                    "Total Close": "Close cost",
                    "Saving": "Saving / extra cost",
                    "EMI Freed": "EMI freed",
                }).style.format({
                    "Close cost": "₹{:,.0f}",
                    "Saving / extra cost": "₹{:,.0f}",
                    "EMI freed": "₹{:,.0f}",
                }),
                use_container_width=True,
                hide_index=True,
            )

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

    st.subheader("What happens if you rotate 1 / 2 / 3 cards?")
    fee = float(get_setting("cheq_fee_per_card", 2000))
    sim = pd.DataFrame({
        "Cards rotated": [1, 2, 3],
        "Approx. fee / cycle": [fee, 2*fee, 3*fee],
        "Approx. annual fee if monthly": [12*fee, 24*fee, 36*fee],
    })
    st.dataframe(
        sim.style.format({
            "Approx. fee / cycle": "₹{:,.0f}",
            "Approx. annual fee if monthly": "₹{:,.0f}",
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

    st.subheader("Add another expense")
    with st.form("expense_add"):
        name = st.text_input("Expense name")
        amount = st.number_input("Monthly amount", min_value=0.0, step=100.0)
        add = st.form_submit_button("Add")
    if add and name.strip():
        conn = db()
        conn.execute(
            "INSERT OR REPLACE INTO expenses(category,planned,active) VALUES(?,?,1)",
            (name.strip(), amount)
        )
        conn.commit()
        conn.close()
        st.success("Expense added.")
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
        st.success("✅ Friend help is currently **ON** — foreclosures are applied to the forecast.")
    else:
        st.warning(
            "⚠️ Friend help is currently **OFF** — the forecast shows baseline EMI. "
            "Draw an amount below and enable it to apply foreclosures."
        )

    st.info(
        "Friend money is a **lump-sum withdrawal**, not monthly income. "
        "It only helps your monthly cash flow after you use it to close loans. "
        "Choose exactly how much to draw using the controls below."
    )

    st.divider()

    # ---------------------------------------------------------
    # 1. Choose how much of the friend money to draw
    # ---------------------------------------------------------
    st.subheader("1. Choose how much of the friend money to draw")

    available_to_draw = max(0.0, amount - used)

    draw_amount = st.number_input(
        "Amount to draw from friend",
        min_value=0.0,
        max_value=float(available_to_draw),
        value=float(min(available_to_draw, 400000)),
        step=5000.0,
        help=f"You have {money(available_to_draw)} left un-drawn out of {money(amount)}.",
    )

    st.caption(
        f"Available to draw: **{money(available_to_draw)}** "
        f"(Agreed {money(amount)} − Already withdrawn {money(used)})"
    )

    # ---------------------------------------------------------
    # 2. Pick which loans the draw should close
    # ---------------------------------------------------------
    st.subheader("2. Pick which loans to close with this draw")

    loans = loans_df()
    closable = loans[(loans["foreclosure_amount"] > 0) & (loans["remaining_months"] > 0)].copy()
    closable["Total Close"] = closable["foreclosure_amount"] + closable["foreclosure_charge"]

    if closable.empty:
        st.warning("No loans have a foreclosure quote entered yet.")
    else:
        closable["Suggested"] = closable["name"].isin(
            ["Flexipay", "Stashfin", "Instamoney"]
        )
        closable = closable.sort_values(
            ["Suggested", "Total Close"], ascending=[False, False]
        )

        options = closable["name"].tolist()
        default_sel = closable[closable["Suggested"]]["name"].tolist()

        selected_loans = st.multiselect(
            "Loans to foreclose with friend money",
            options=options,
            default=default_sel,
        )

        chosen = closable[closable["name"].isin(selected_loans)]
        loan_cost = float(chosen["Total Close"].sum()) if not chosen.empty else 0.0
        emi_freed = float(chosen["emi"].sum()) if not chosen.empty else 0.0

        st.write(
            f"Selected loans close cost: **{money(loan_cost)}** "
            f"| EMI freed: **{money(emi_freed)}/month**"
        )

    # ---------------------------------------------------------
    # 3. Optional card clearance
    # ---------------------------------------------------------
    st.subheader("3. Clear cards with the same draw?")
    cards = cards_df()
    total_card_bal = float(cards["balance"].sum()) if not cards.empty else 0
    clear_cards = st.checkbox(
        f"Yes, clear all card balances ({money(total_card_bal)})",
        value=(total_card_bal > 0),
    )
    card_cost = total_card_bal if clear_cards else 0.0

    # ---------------------------------------------------------
    # 4. Check the draw covers the chosen package
    # ---------------------------------------------------------
    st.subheader("4. Summary")
    total_use = loan_cost + card_cost
    leftover = draw_amount - total_use

    s1, s2, s3, s4 = st.columns(4)
    s1.metric("Draw amount", money(draw_amount))
    s2.metric("Loans to close", money(loan_cost))
    s3.metric("Cards to clear", money(card_cost))
    s4.metric("Left un-used from draw", money(max(0, leftover)))

    if total_use > draw_amount:
        st.error(
            f"❌ Selected package costs {money(total_use)}, "
            f"but your draw is only {money(draw_amount)}. "
            "Reduce the loan selection, uncheck cards, or increase the draw."
        )
    else:
        st.success(
            f"✅ Draw of {money(draw_amount)} covers the package "
            f"({money(total_use)}) and frees {money(emi_freed)}/month."
        )

    # ---------------------------------------------------------
    # 5. Apply
    # ---------------------------------------------------------
    apply_disabled = total_use > draw_amount or total_use <= 0
    apply = st.button(
        "🚀 Apply draw & foreclosures",
        type="primary",
        disabled=apply_disabled,
    )

    if apply:
        conn = db()
        forecast_date = pd.to_datetime(
            get_setting("forecast_start", "2026-10-01")
        ).date().isoformat()

        # Remove any existing "Planned" foreclosures from a previous run
        conn.execute("DELETE FROM foreclosures WHERE status='Planned'")

        # Insert new foreclosures
        for _, r in chosen.iterrows():
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

        # Clear cards if chosen
        if clear_cards:
            conn.execute("UPDATE cards SET balance=0, minimum_due=0 WHERE active=1")

        conn.commit()
        conn.close()

        # Update friend usage / balance
        new_used = used + total_use
        new_balance = max(0.0, amount - new_used)

        set_setting("friend_amount_used", new_used)
        set_setting("friend_balance", new_balance)
        set_setting("friend_help_enabled", "1")

        st.success(
            f"Applied. Friend help is now ON. "
            f"Used {money(total_use)}, outstanding to friend {money(new_balance)}."
        )
        st.rerun()

    # ---------------------------------------------------------
    # Quick reset
    # ---------------------------------------------------------
    if used > 0 or enabled:
        st.divider()
        st.subheader("Reset friend help")
        st.caption("This clears all Planned foreclosures, restores card balances is NOT automatic — update them manually if needed, and sets friend help to OFF.")
        if st.button("🔁 Reset friend help (keep card balances as-is)"):
            conn = db()
            conn.execute("DELETE FROM foreclosures WHERE status='Planned'")
            conn.commit()
            conn.close()
            set_setting("friend_amount_used", 0)
            set_setting("friend_balance", amount)
            set_setting("friend_help_enabled", "0")
            st.success("Friend help reset.")
            st.rerun()

    st.divider()
    st.subheader("Step-up rules")
    st.write("""
    - Negative cash flow → ₹0 friend payment
    - ₹0–₹10k cash flow → ₹10k
    - ₹10k–₹20k → ₹15k
    - ₹20k–₹30k → ₹25k
    - ₹30k–₹40k → ₹30k
    - Above ₹40k → ₹40k
    - Repayment never pushes Cash Flow After Friend below zero.
    """)

    st.subheader("Projected step-up schedule")
    current_planned = planned_foreclosures_df()
    if not enabled:
        st.warning(
            "⚠️ Friend help is OFF. The schedule below is the **baseline EMI burden**. "
            "Draw an amount above and click Apply to switch to the reduced-EMI view."
        )
    elif not current_planned.empty:
        freed = float(current_planned["emi"].sum())
        st.success(
            f"✅ Forecast is using {len(current_planned)} planned foreclosure(s) and "
            f"has removed {money(freed)}/month of EMI."
        )

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

    st.subheader("Manual repayment log")
    with st.form("friend_payment"):
        pdate = st.date_input("Payment date", value=date.today())
        pamt = st.number_input("Payment amount", min_value=0.0, step=1000.0)
        desc = st.text_input("Description", value="Friend repayment")
        save = st.form_submit_button("Record payment")
    if save and pamt > 0:
        new_balance = max(0, balance - pamt)
        set_setting("friend_balance", new_balance)
        conn = db()
        conn.execute(
            "INSERT INTO payments(payment_date,category,description,amount) VALUES(?,?,?,?)",
            (pdate.isoformat(), "Friend Loan", desc, pamt)
        )
        conn.commit()
        conn.close()
        st.success(f"Recorded {money(pamt)}. Friend balance is now {money(new_balance)}.")
        st.rerun()

# -----------------------------
# Settings
# -----------------------------
elif page == "⚙️ Settings":
    st.title("⚙️ Settings")

    st.subheader("Income & cash")
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
            min_value=0.0,
            step=100.0,
        )
        cash = st.number_input(
            "Starting / available cash",
            value=float(get_setting("starting_cash", 20000)),
            min_value=0.0,
            step=1000.0,
        )
        bonus = st.number_input(
            "Current-month bonus",
            value=float(get_setting("bonus_current_month", 0)),
            min_value=0.0,
            step=1000.0,
        )
        forecast_start = st.date_input(
            "Forecast start month",
            value=pd.to_datetime(get_setting("forecast_start", "2026-10-01")).date(),
        )
        cheq = st.number_input(
            "CheQ fee per rotated card",
            value=float(get_setting("cheq_fee_per_card", 2000)),
            min_value=0.0,
            step=100.0,
        )
        save = st.form_submit_button("Save settings")

    if save:
        set_setting("monthly_salary", salary)
        set_setting("future_salary", future_salary)
        set_setting("future_salary_start", future_start.isoformat())
        set_setting("pf_monthly", pf)
        set_setting("starting_cash", cash)
        set_setting("bonus_current_month", bonus)
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
        help="When OFF, forecast shows baseline EMI. When ON, planned foreclosures are applied.",
    )
    if new_state != friend_on_now:
        set_setting("friend_help_enabled", "1" if new_state else "0")
        st.rerun()

    st.divider()
    st.subheader("Current setup summary")
    st.write({
        "Salary now": money(float(get_setting("monthly_salary"))),
        "Expected salary": money(float(get_setting("future_salary"))),
        "PF/month": money(float(get_setting("pf_monthly"))),
        "Friend help agreed": money(float(get_setting("friend_help_amount"))),
        "Friend withdrawn": money(float(get_setting("friend_amount_used", 0))),
        "Friend outstanding": money(float(get_setting("friend_balance"))),
        "Friend help enabled": "ON" if get_setting_bool("friend_help_enabled") else "OFF",
        "Living expenses": money(total_living()),
        "Loan EMI (raw)": money(total_emi()),
        "Card balance": money(total_cards()),
    })

    st.divider()
    st.subheader("Important")
    st.warning(
        "The app uses the foreclosure quotes you enter. Before actually paying a lender, "
        "verify the live foreclosure amount, charges, closure confirmation and any pending EMI."
    )
