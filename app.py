
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

    # Default settings
    defaults = {
        "monthly_salary": "65000",
        "future_salary": "75000",
        "future_salary_start": "2026-11-01",
        "pf_monthly": "1800",
        "friend_help_amount": "400000",
        "friend_balance": "400000",
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

    # Seed loans only when absent
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

    rows = []
    for i, m in enumerate(months_from(start, months)):
        salary = base_salary if m < future_start else future_salary
        if salary_override is not None:
            salary = salary_override

        emi, detail = loan_emi_for_months(loans, i)
        cards = total_cards()
        cash_flow = salary - living - emi
        rows.append({
            "Month": m.strftime("%b %Y"),
            "Salary": salary,
            "Living": living,
            "EMI": emi,
            "Cash Flow Before Friend": cash_flow,
            "Card Balance": cards,
            "Loan EMI Count": sum(1 for _, e in detail if e > 0),
        })
    return pd.DataFrame(rows)

def friend_plan(months=24):
    f = forecast_df(months)
    balance = float(get_setting("friend_balance", get_setting("friend_help_amount", 400000)))
    start = pd.to_datetime(get_setting("forecast_start", "2026-10-01"))

    # Dynamic repayment: low while cash flow is negative, then increasing as
    # cash flow improves. The user can override individual targets in Settings.
    repayments = []
    for _, r in f.iterrows():
        cf = float(r["Cash Flow Before Friend"])
        if balance <= 0:
            pay = 0
        elif cf <= 0:
            pay = 5000
        elif cf < 10000:
            pay = 10000
        elif cf < 20000:
            pay = 15000
        elif cf < 30000:
            pay = 25000
        elif cf < 40000:
            pay = 35000
        else:
            pay = 40000

        # Never plan more than the remaining friend balance.
        pay = min(pay, balance)
        repayments.append(pay)
        balance -= pay

    f["Friend Repayment"] = repayments
    f["Cash Flow After Friend"] = f["Cash Flow Before Friend"] - f["Friend Repayment"]
    f["Friend Balance"] = [
        max(0, float(get_setting("friend_balance", 400000)) - sum(repayments[:i+1]))
        for i in range(len(repayments))
    ]
    return f

# -----------------------------
# Sidebar
# -----------------------------
st.sidebar.title("💰 Debt Command Center")
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
    st.caption("This app is designed to tell you what to do with your cash — not just record it.")

    salary = float(get_setting("monthly_salary", 65000))
    future_salary = float(get_setting("future_salary", 75000))
    living = total_living()
    emi = total_emi()
    cards = total_cards()
    friend = float(get_setting("friend_balance", get_setting("friend_help_amount", 400000)))
    cash = float(get_setting("starting_cash", 20000))
    pf = float(get_setting("pf_monthly", 1800))

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Current take-home", money(salary))
    c2.metric("Future target salary", money(future_salary))
    c3.metric("Current loan EMIs", money(emi))
    c4.metric("Card balances", money(cards))

    st.divider()

    # Current cashflow
    current_cf = salary - living - emi
    st.subheader("1. Your current monthly position")
    a, b, c, d = st.columns(4)
    a.metric("Living costs", money(living))
    b.metric("Loan EMIs", money(emi))
    c.metric("Cash flow before friend", money(current_cf))
    d.metric("PF added monthly", money(pf))

    if current_cf < 0:
        st.error(
            f"⚠️ You are short by {money(abs(current_cf))} before any friend repayment. "
            "Do not take a new loan to cover this gap."
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
            f"Recent logged CheQ fees: {money(recent_fees)}. "
            "Clearing a card and then recycling it through CheQ does not eliminate the debt."
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
        "Forecast uses your editable salary assumptions, living expenses, remaining EMI months, "
        "and step-up friend repayment rules. It does not assume a future bonus unless you enter one."
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
    st.title("🤝 Friend Loan — Step-Up Repayment Manager")

    amount = float(get_setting("friend_help_amount", 400000))
    balance = float(get_setting("friend_balance", amount))
    target = get_setting("friend_target_date", "2028-03-31")

    c1, c2, c3 = st.columns(3)
    c1.metric("Original friend help", money(amount))
    c2.metric("Current friend balance", money(balance))
    c3.metric("Target date", target)

    st.info(
        "The friend-help amount is fully editable. The app treats this as a separate debt "
        "and automatically increases the suggested payment as salary rises and EMIs disappear."
    )

    st.subheader("Step-up rules")
    st.write("""
    The built-in rule is intentionally conservative:
    - Negative cash flow → ₹5k friend payment
    - ₹0–₹10k cash flow → ₹10k
    - ₹10k–₹20k → ₹15k
    - ₹20k–₹30k → ₹25k
    - ₹30k–₹40k → ₹35k
    - Above ₹40k → ₹40k
    """)

    with st.form("friend_settings"):
        new_amount = st.number_input(
            "Friend help amount",
            value=amount,
            min_value=0.0,
            step=5000.0,
        )
        new_balance = st.number_input(
            "Current friend balance",
            value=balance,
            min_value=0.0,
            step=5000.0,
        )
        target_date = st.date_input(
            "Target repayment date",
            value=pd.to_datetime(target).date(),
        )
        save = st.form_submit_button("Save friend-loan settings")

    if save:
        set_setting("friend_help_amount", new_amount)
        set_setting("friend_balance", new_balance)
        set_setting("friend_target_date", target_date.isoformat())
        st.success("Friend-loan settings saved.")
        st.rerun()

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
    st.subheader("Current setup summary")
    st.write({
        "Salary now": money(float(get_setting("monthly_salary"))),
        "Expected salary": money(float(get_setting("future_salary"))),
        "PF/month": money(float(get_setting("pf_monthly"))),
        "Friend help": money(float(get_setting("friend_help_amount"))),
        "Friend balance": money(float(get_setting("friend_balance"))),
        "Living expenses": money(total_living()),
        "Loan EMI": money(total_emi()),
        "Card balance": money(total_cards()),
    })

    st.divider()
    st.subheader("Important")
    st.warning(
        "The app uses the foreclosure quotes you enter. Before actually paying a lender, "
        "verify the live foreclosure amount, charges, closure confirmation and any pending EMI."
    )
