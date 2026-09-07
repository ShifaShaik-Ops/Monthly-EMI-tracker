import streamlit as st
import sqlite3
import pandas as pd
from datetime import date
import calendar
import os

# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Debt Command Center",
    page_icon="💰",
    layout="wide",
)

DB_FILE = "debt_manager.db"

FORECAST_YEAR = 2026
FORECAST_MONTH = 10

# ============================================================
# DEFAULT FINANCIAL DATA
# ============================================================

DEFAULT_SALARY = 59000
DEFAULT_BONUS = 60000
DEFAULT_CASH = 40000
DEFAULT_FRIEND_REPAYMENT = 80000
DEFAULT_CHEQ_FEE = 2000

LIVING_EXPENSES = {
    "Rent": 15000,
    "Fuel": 2000,
    "Grocery": 2000,
    "Miscellaneous": 2000,
    "JioFiber": 1200,
    "Salon": 2000,
}

DEFAULT_LOANS = [
    ("Fibe", 9890, 6, 4, ""),
    ("Stashfin", 4199, 11, 2, "Rotatable only if needed"),
    ("Kredibee", 9219, 5, 2, ""),
    ("Branch", 2488, 4, 28, ""),
    ("Money View", 3764, 5, 3, ""),
    ("Poonawala Fincorp", 6507, 21, 5, ""),
    ("Instamoney", 5616, 2, 1, "Rotatable only if needed"),
    ("Kissht", 1583, 8, 7, ""),
    ("Loan Tap", 5276, 1, 1, ""),
    ("Flexipay", 6000, 23, 26, ""),
]

DEFAULT_CARDS = [
    ("Axis", 60000, 0, ""),
    ("HDFC", 29656, 1816, "2026-08-28"),
    ("DBS", 36000, 1089.79, "2026-09-01"),
]


# ============================================================
# FORMATTING
# ============================================================

def money(value):
    try:
        value = float(value or 0)
    except (TypeError, ValueError):
        value = 0.0

    sign = "-" if value < 0 else ""
    value = abs(value)

    return f"{sign}₹{value:,.0f}"


def money2(value):
    try:
        value = float(value or 0)
    except (TypeError, ValueError):
        value = 0.0

    return f"₹{value:,.2f}"


def add_months(year, month, n):
    total = year * 12 + month - 1 + n
    return total // 12, total % 12 + 1


def month_label(year, month):
    return f"{calendar.month_name[month]} {year}"


# ============================================================
# DATABASE
# ============================================================

def get_db():
    return sqlite3.connect(
        DB_FILE,
        check_same_thread=False
    )


def table_exists(conn, table_name):
    cur = conn.cursor()

    cur.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type='table'
        AND name=?
        """,
        (table_name,)
    )

    return cur.fetchone() is not None


def get_columns(conn, table_name):
    cur = conn.cursor()

    try:
        cur.execute(
            f"PRAGMA table_info({table_name})"
        )

        return [
            row[1]
            for row in cur.fetchall()
        ]

    except Exception:
        return []


# ============================================================
# DATABASE SETUP / MIGRATION
# ============================================================

def setup_database():

    conn = get_db()
    cur = conn.cursor()

    # --------------------------------------------------------
    # SETTINGS
    # --------------------------------------------------------

    cur.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    # --------------------------------------------------------
    # LOANS
    # --------------------------------------------------------

    if not table_exists(conn, "loans"):

        cur.execute("""
            CREATE TABLE loans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                emi REAL,
                months_left INTEGER,
                emi_date INTEGER,
                notes TEXT
            )
        """)

    else:

        columns = get_columns(conn, "loans")

        if "months_left" not in columns:

            cur.execute("""
                ALTER TABLE loans
                ADD COLUMN months_left INTEGER DEFAULT 0
            """)

        if "emi_date" not in columns:

            cur.execute("""
                ALTER TABLE loans
                ADD COLUMN emi_date INTEGER DEFAULT 1
            """)

        if "notes" not in columns:

            cur.execute("""
                ALTER TABLE loans
                ADD COLUMN notes TEXT DEFAULT ''
            """)

    # --------------------------------------------------------
    # CARDS
    # --------------------------------------------------------

    if not table_exists(conn, "cards"):

        cur.execute("""
            CREATE TABLE cards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                balance REAL,
                minimum_due REAL,
                due_date TEXT
            )
        """)

    else:

        columns = get_columns(conn, "cards")

        if "minimum_due" not in columns:

            cur.execute("""
                ALTER TABLE cards
                ADD COLUMN minimum_due REAL DEFAULT 0
            """)

        if "due_date" not in columns:

            cur.execute("""
                ALTER TABLE cards
                ADD COLUMN due_date TEXT DEFAULT ''
            """)

    # --------------------------------------------------------
    # PAYMENTS
    # --------------------------------------------------------

    cur.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            loan_id INTEGER,
            payment_date TEXT,
            amount REAL,
            note TEXT
        )
    """)

    # --------------------------------------------------------
    # FORECLOSURES
    # --------------------------------------------------------

    cur.execute("""
        CREATE TABLE IF NOT EXISTS foreclosures (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            loan_id INTEGER,
            quote_date TEXT,
            foreclosure_amount REAL,
            valid_until TEXT,
            note TEXT
        )
    """)

    # --------------------------------------------------------
    # CARD ROTATIONS
    # --------------------------------------------------------

    cur.execute("""
        CREATE TABLE IF NOT EXISTS card_rotations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            card_name TEXT,
            rotation_date TEXT,
            amount REAL,
            fee REAL
        )
    """)

    # --------------------------------------------------------
    # EXPENSES
    # --------------------------------------------------------

    cur.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT,
            amount REAL,
            expense_date TEXT
        )
    """)

    conn.commit()

    # --------------------------------------------------------
    # INSERT DEFAULT LOANS ONLY IF MISSING
    # --------------------------------------------------------

    cur.execute(
        "SELECT COUNT(*) FROM loans"
    )

    loan_count = cur.fetchone()[0]

    if loan_count == 0:

        for loan in DEFAULT_LOANS:

            cur.execute("""
                INSERT INTO loans
                (name, emi, months_left, emi_date, notes)
                VALUES (?, ?, ?, ?, ?)
            """, loan)

    # --------------------------------------------------------
    # INSERT DEFAULT CARDS ONLY IF MISSING
    # --------------------------------------------------------

    cur.execute(
        "SELECT COUNT(*) FROM cards"
    )

    card_count = cur.fetchone()[0]

    if card_count == 0:

        for card in DEFAULT_CARDS:

            cur.execute("""
                INSERT INTO cards
                (name, balance, minimum_due, due_date)
                VALUES (?, ?, ?, ?)
            """, card)

    conn.commit()
    conn.close()


setup_database()


# ============================================================
# SETTINGS FUNCTIONS
# ============================================================

def get_setting(key, default):

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "SELECT value FROM settings WHERE key=?",
        (key,)
    )

    row = cur.fetchone()

    conn.close()

    if row is None:
        return default

    try:
        return float(row[0])
    except Exception:
        return row[0]


def save_setting(key, value):

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO settings(key, value)
        VALUES (?, ?)
        ON CONFLICT(key)
        DO UPDATE SET value=excluded.value
    """, (
        key,
        str(value)
    ))

    conn.commit()
    conn.close()


# ============================================================
# LOADERS
# ============================================================

def load_loans():

    conn = get_db()

    df = pd.read_sql_query(
        """
        SELECT
            id,
            name,
            emi,
            months_left,
            emi_date,
            notes
        FROM loans
        ORDER BY id
        """,
        conn
    )

    conn.close()

    return df


def load_cards():

    conn = get_db()

    df = pd.read_sql_query(
        """
        SELECT
            id,
            name,
            balance,
            minimum_due,
            due_date
        FROM cards
        ORDER BY id
        """,
        conn
    )

    conn.close()

    return df


def load_foreclosures():

    conn = get_db()

    # IMPORTANT:
    # This query only uses tables guaranteed by setup_database().
    df = pd.read_sql_query(
        """
        SELECT
            f.id,
            f.loan_id,
            f.quote_date,
            f.foreclosure_amount,
            f.valid_until,
            f.note,
            l.name AS loan_name,
            l.emi,
            l.months_left
        FROM foreclosures f
        LEFT JOIN loans l
        ON f.loan_id = l.id
        ORDER BY f.quote_date DESC
        """,
        conn
    )

    conn.close()

    return df


def load_rotations():

    conn = get_db()

    df = pd.read_sql_query(
        """
        SELECT
            id,
            card_name,
            rotation_date,
            amount,
            fee
        FROM card_rotations
        ORDER BY rotation_date DESC
        """,
        conn
    )

    conn.close()

    return df


# ============================================================
# LOAD CURRENT DATA
# ============================================================

salary = float(
    get_setting(
        "salary",
        DEFAULT_SALARY
    )
)

bonus = float(
    get_setting(
        "bonus",
        DEFAULT_BONUS
    )
)

cash = float(
    get_setting(
        "cash",
        DEFAULT_CASH
    )
)

friend_repayment = float(
    get_setting(
        "friend_repayment",
        DEFAULT_FRIEND_REPAYMENT
    )
)

cheq_fee = float(
    get_setting(
        "cheq_fee",
        DEFAULT_CHEQ_FEE
    )
)

loans = load_loans()
cards = load_cards()
foreclosures = load_foreclosures()
rotations = load_rotations()

living_total = sum(
    LIVING_EXPENSES.values()
)


# ============================================================
# FORECAST
# ============================================================

def make_forecast(months=24):

    rows = []

    for i in range(months):

        year, month = add_months(
            FORECAST_YEAR,
            FORECAST_MONTH,
            i
        )

        emi_total = 0
        active_loans = 0

        for _, loan in loans.iterrows():

            remaining = max(
                0,
                int(loan["months_left"]) - i
            )

            if remaining > 0:

                emi_total += float(
                    loan["emi"]
                )

                active_loans += 1

        cash_flow = (
            salary
            - living_total
            - emi_total
        )

        rows.append({
            "month": month_label(
                year,
                month
            ),
            "salary": salary,
            "living": living_total,
            "emi": emi_total,
            "cash_flow": cash_flow,
            "active_loans": active_loans
        })

    return pd.DataFrame(rows)


forecast = make_forecast()


# ============================================================
# HEADER
# ============================================================

st.title("💰 Debt Command Center")

st.caption(
    "A decision system for managing the EMI shortage "
    "without automatically taking another loan."
)

st.info(
    "📅 Forecast starts from 26 September 2026. "
    "September EMIs are already treated as paid."
)


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.header("💰 Snapshot")

    st.metric(
        "Salary",
        money(salary)
    )

    st.metric(
        "Living Expenses",
        money(living_total)
    )

    total_emi = (
        loans["emi"].sum()
        if not loans.empty
        else 0
    )

    st.metric(
        "EMIs",
        money(total_emi)
    )

    monthly_flow = (
        salary
        - living_total
        - total_emi
    )

    st.metric(
        "Monthly Cash Flow",
        money(monthly_flow)
    )

    st.divider()

    st.caption(
        "Start: 26 Sep 2026"
    )

    st.caption(
        "Forecast: October 2026 onward"
    )


# ============================================================
# TABS
# ============================================================

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    [
        "🚨 COMMAND CENTER",
        "📊 FORECAST",
        "🏦 LOANS",
        "💳 CARDS + CHEQ",
        "⚙️ SETTINGS",
    ]
)


# ============================================================
# COMMAND CENTER
# ============================================================

with tab1:

    st.header("🚨 NO NEW LOAN PLAN")

    # --------------------------------------------------------
    # CASH POSITION
    # --------------------------------------------------------

    cash_after_friend = (
        cash
        + bonus
        - friend_repayment
    )

    a, b, c, d = st.columns(4)

    with a:
        st.metric(
            "Current Cash",
            money(cash)
        )

    with b:
        st.metric(
            "Bonus",
            money(bonus)
        )

    with c:
        st.metric(
            "Friend Repayment",
            money(friend_repayment)
        )

    with d:
        st.metric(
            "Cash After Friend",
            money(cash_after_friend)
        )

    if cash_after_friend >= 0:

        st.success(
            f"After paying your friend, "
            f"you have approximately "
            f"**{money(cash_after_friend)}**."
        )

    else:

        st.error(
            "Your cash is insufficient even before the EMI bridge."
        )

    # --------------------------------------------------------
    # CURRENT POSITION
    # --------------------------------------------------------

    st.subheader("1️⃣ Monthly Reality")

    current_emi = (
        loans["emi"].sum()
        if not loans.empty
        else 0
    )

    current_flow = (
        salary
        - living_total
        - current_emi
    )

    x, y, z = st.columns(3)

    with x:
        st.metric(
            "Salary",
            money(salary)
        )

    with y:
        st.metric(
            "Living",
            money(living_total)
        )

    with z:
        st.metric(
            "EMIs",
            money(current_emi)
        )

    if current_flow < 0:

        st.error(
            f"Current monthly shortage: "
            f"**{money(abs(current_flow))}**."
        )

    else:

        st.success(
            f"Current monthly surplus: "
            f"**{money(current_flow)}**."
        )

    # --------------------------------------------------------
    # BRIDGE CALCULATION
    # --------------------------------------------------------

    st.subheader("2️⃣ EMI Bridge")

    cumulative = 0
    lowest = 0
    lowest_month = None

    bridge_rows = []

    for _, row in forecast.head(12).iterrows():

        cumulative += row["cash_flow"]

        if cumulative < lowest:

            lowest = cumulative
            lowest_month = row["month"]

        bridge_rows.append({
            "Month": row["month"],
            "EMIs": row["emi"],
            "Monthly Cash Flow": row["cash_flow"],
            "Cumulative Cash Flow": cumulative
        })

    bridge_need = abs(
        min(
            0,
            lowest
        )
    )

    if bridge_need > 0:

        st.warning(
            f"Maximum modeled bridge requirement: "
            f"**{money(bridge_need)}**."
        )

        if cash_after_friend >= bridge_need:

            st.success(
                "Your current post-friend cash can cover "
                "the modeled EMI bridge."
            )

        else:

            remaining_gap = (
                bridge_need
                - cash_after_friend
            )

            st.error(
                f"Additional bridge required: "
                f"**{money(remaining_gap)}**."
            )

    # --------------------------------------------------------
    # POSITIVE MONTH
    # --------------------------------------------------------

    positive_month = None

    for _, row in forecast.iterrows():

        if row["cash_flow"] >= 0:

            positive_month = row["month"]
            break

    if positive_month:

        st.success(
            f"🎯 Monthly cash flow becomes positive around "
            f"**{positive_month}**."
        )

    # --------------------------------------------------------
    # TABLE
    # --------------------------------------------------------

    bridge_display = pd.DataFrame(
        bridge_rows
    )

    for column in [
        "EMIs",
        "Monthly Cash Flow",
        "Cumulative Cash Flow"
    ]:

        bridge_display[column] = (
            bridge_display[column]
            .apply(money)
        )

    st.dataframe(
        bridge_display,
        use_container_width=True,
        hide_index=True
    )

    # --------------------------------------------------------
    # STRATEGY
    # --------------------------------------------------------

    st.subheader("3️⃣ Recommended Strategy")

    if current_flow < 0:

        st.markdown("""
### Phase 1 — Survive the bridge

**Priority order:**

1. Keep enough cash for upcoming EMIs.
2. Pay the friend loan as planned.
3. Do not take a new long-term loan for a temporary shortage.
4. Cut discretionary expenses wherever possible.
5. If necessary, use the minimum required card rotation.
6. Keep track of every CheQ fee.
7. Only consider foreclosure if it improves monthly cash flow **without destroying your bridge cash**.
8. Once monthly cash flow turns positive, stop unnecessary card rotation.
        """)

    else:

        st.markdown("""
### Phase 2 — Attack debt

1. Stop unnecessary card rotation.
2. Attack credit-card balances.
3. When an EMI finishes, redirect that EMI to debt.
4. Avoid increasing lifestyle expenses.
5. Build an emergency reserve.
        """)

    # ========================================================
    # FORECLOSURE ENGINE
    # ========================================================

    st.divider()

    st.subheader(
        "4️⃣ 🏦 Foreclosure Decision Engine"
    )

    st.write(
        "Enter the actual foreclosure quote from the lender."
    )

    st.caption(
        "Do NOT assume EMI × remaining months is the foreclosure amount."
    )

    if loans.empty:

        st.info(
            "No loans found."
        )

    else:

        active_loans = loans[
            loans["months_left"] > 0
        ].copy()

        if active_loans.empty:

            st.success(
                "No active loans."
            )

        else:

            selected_name = st.selectbox(
                "Loan",
                active_loans["name"].tolist()
            )

            selected = active_loans[
                active_loans["name"]
                == selected_name
            ].iloc[0]

            c1, c2, c3 = st.columns(3)

            with c1:

                st.metric(
                    "EMI",
                    money(selected["emi"])
                )

            with c2:

                st.metric(
                    "Months Left",
                    int(selected["months_left"])
                )

            with c3:

                st.metric(
                    "Scheduled Remaining",
                    money(
                        selected["emi"]
                        * selected["months_left"]
                    )
                )

            foreclosure_quote = st.number_input(
                "Actual foreclosure amount",
                min_value=0.0,
                step=1000.0,
                value=0.0
            )

            if foreclosure_quote > 0:

                cash_remaining = (
                    cash_after_friend
                    - foreclosure_quote
                )

                emi_saved = float(
                    selected["emi"]
                )

                efficiency = (
                    emi_saved
                    / foreclosure_quote
                )

                improved_cash_flow = (
                    current_flow
                    + emi_saved
                )

                st.write(
                    f"Cash remaining after foreclosure: "
                    f"**{money(cash_remaining)}**"
                )

                st.write(
                    f"Monthly EMI removed: "
                    f"**{money(emi_saved)}**"
                )

                st.write(
                    f"Monthly cash-flow improvement: "
                    f"**{money(emi_saved)}**"
                )

                st.write(
                    f"Efficiency: "
                    f"**{efficiency:.5f} EMI/₹**"
                )

                if cash_remaining < bridge_need:

                    st.error(
                        "❌ NOT RECOMMENDED RIGHT NOW"
                    )

                    st.write(
                        "This foreclosure would leave you with "
                        "less cash than the modeled bridge requirement."
                    )

                else:

                    st.success(
                        "This foreclosure does not destroy "
                        "the modeled bridge reserve."
                    )

                    st.write(
                        f"New monthly cash flow would be "
                        f"**{money(improved_cash_flow)}**."
                    )

                    if improved_cash_flow >= 0:

                        st.success(
                            "🎯 This could eliminate the current "
                            "monthly deficit."
                        )

                    else:

                        st.warning(
                            "This helps but does not fully "
                            "eliminate the monthly deficit."
                        )

                if st.button(
                    "💾 Save Foreclosure Quote",
                    key="save_foreclosure"
                ):

                    conn = get_db()
                    cur = conn.cursor()

                    cur.execute("""
                        INSERT INTO foreclosures
                        (
                            loan_id,
                            quote_date,
                            foreclosure_amount,
                            valid_until,
                            note
                        )
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        int(selected["id"]),
                        str(date.today()),
                        foreclosure_quote,
                        "",
                        "Manual lender quote"
                    ))

                    conn.commit()
                    conn.close()

                    st.success(
                        "Foreclosure quote saved."
                    )

                    st.rerun()

    # ========================================================
    # BEST FORECLOSURE
    # ========================================================

    st.divider()

    st.subheader(
        "5️⃣ 🏆 Best Saved Foreclosure Option"
    )

    if foreclosures.empty:

        st.info(
            "Save actual lender foreclosure quotes above "
            "to compare them."
        )

    else:

        comparison = foreclosures.copy()

        comparison = comparison[
            comparison["foreclosure_amount"] > 0
        ].copy()

        if comparison.empty:

            st.info(
                "No valid foreclosure quotes yet."
            )

        else:

            comparison["efficiency"] = (
                comparison["emi"]
                / comparison["foreclosure_amount"]
            )

            comparison = comparison.sort_values(
                "efficiency",
                ascending=False
            )

            best = comparison.iloc[0]

            st.success(
                f"Best monthly-cash-flow efficiency: "
                f"**{best['loan_name']}**"
            )

            st.write(
                f"EMI: **{money(best['emi'])}**"
            )

            st.write(
                f"Foreclosure quote: "
                f"**{money(best['foreclosure_amount'])}**"
            )

            st.write(
                f"Monthly EMI reduction per ₹ spent: "
                f"**{best['efficiency']:.5f}**"
            )

    # ========================================================
    # NEW LOAN TEST
    # ========================================================

    st.divider()

    st.subheader(
        "6️⃣ 🚫 New Loan Test"
    )

    proposed_emi = st.number_input(
        "Proposed new EMI",
        min_value=0.0,
        step=500.0,
        value=0.0
    )

    if proposed_emi > 0:

        new_flow = (
            current_flow
            - proposed_emi
        )

        st.write(
            f"Current monthly cash flow: "
            f"**{money(current_flow)}**"
        )

        st.write(
            f"After new EMI: "
            f"**{money(new_flow)}**"
        )

        if current_flow < 0:

            st.error(
                "🚨 You already have a monthly deficit. "
                "Taking another EMI makes the structural problem worse."
            )

        elif new_flow < 0:

            st.warning(
                "The new loan would push your monthly cash flow "
                "into negative territory."
            )

        else:

            st.info(
                "The new EMI does not create a monthly deficit "
                "under these assumptions, but compare total repayment."
            )


# ============================================================
# FORECAST TAB
# ============================================================

with tab2:

    st.header("📊 24-Month Forecast")

    display = forecast.copy()

    display = display.rename(
        columns={
            "month": "Month",
            "salary": "Salary",
            "living": "Living Expenses",
            "emi": "EMIs",
            "cash_flow": "Monthly Cash Flow",
            "active_loans": "Active Loans"
        }
    )

    for column in [
        "Salary",
        "Living Expenses",
        "EMIs",
        "Monthly Cash Flow"
    ]:

        display[column] = (
            display[column]
            .apply(money)
        )

    st.dataframe(
        display,
        use_container_width=True,
        hide_index=True
    )

    st.subheader("EMI Trend")

    emi_chart = forecast[
        ["month", "emi"]
    ].copy()

    emi_chart = emi_chart.set_index(
        "month"
    )

    st.line_chart(
        emi_chart
    )

    st.subheader("Cash-Flow Trend")

    flow_chart = forecast[
        ["month", "cash_flow"]
    ].copy()

    flow_chart = flow_chart.set_index(
        "month"
    )

    st.line_chart(
        flow_chart
    )


# ============================================================
# LOANS TAB
# ============================================================

with tab3:

    st.header("🏦 Loans")

    if not loans.empty:

        loan_display = loans.copy()

        loan_display["emi"] = (
            loan_display["emi"]
            .apply(money)
        )

        loan_display = loan_display.rename(
            columns={
                "name": "Loan",
                "emi": "EMI",
                "months_left": "Months Left",
                "emi_date": "EMI Date",
                "notes": "Notes"
            }
        )

        st.dataframe(
            loan_display[
                [
                    "Loan",
                    "EMI",
                    "Months Left",
                    "EMI Date",
                    "Notes"
                ]
            ],
            use_container_width=True,
            hide_index=True
        )

    st.divider()

    st.subheader(
        "✏️ Update Loan"
    )

    if not loans.empty:

        loan_id = st.selectbox(
            "Select loan",
            loans["id"].tolist(),
            format_func=lambda x:
                loans.loc[
                    loans["id"] == x,
                    "name"
                ].iloc[0]
        )

        selected = loans[
            loans["id"] == loan_id
        ].iloc[0]

        new_emi = st.number_input(
            "EMI",
            min_value=0.0,
            value=float(selected["emi"]),
            step=100.0
        )

        new_months = st.number_input(
            "Months remaining",
            min_value=0,
            max_value=120,
            value=int(selected["months_left"]),
            step=1
        )

        if st.button(
            "Save Loan"
        ):

            conn = get_db()
            cur = conn.cursor()

            cur.execute("""
                UPDATE loans
                SET emi=?, months_left=?
                WHERE id=?
            """, (
                new_emi,
                int(new_months),
                int(loan_id)
            ))

            conn.commit()
            conn.close()

            st.success(
                "Loan updated."
            )

            st.rerun()

    st.divider()

    st.subheader(
        "➕ Add New Loan"
    )

    with st.form("new_loan"):

        loan_name = st.text_input(
            "Loan name"
        )

        loan_emi = st.number_input(
            "EMI",
            min_value=0.0,
            step=100.0
        )

        loan_months = st.number_input(
            "Months remaining",
            min_value=0,
            step=1
        )

        loan_date = st.number_input(
            "EMI date",
            min_value=1,
            max_value=31,
            value=1
        )

        loan_notes = st.text_input(
            "Notes"
        )

        submit = st.form_submit_button(
            "Add Loan"
        )

        if submit:

            if not loan_name.strip():

                st.error(
                    "Enter a loan name."
                )

            elif loan_emi <= 0:

                st.error(
                    "Enter a valid EMI."
                )

            else:

                try:

                    conn = get_db()
                    cur = conn.cursor()

                    cur.execute("""
                        INSERT INTO loans
                        (
                            name,
                            emi,
                            months_left,
                            emi_date,
                            notes
                        )
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        loan_name.strip(),
                        loan_emi,
                        int(loan_months),
                        int(loan_date),
                        loan_notes
                    ))

                    conn.commit()
                    conn.close()

                    st.success(
                        "Loan added."
                    )

                    st.rerun()

                except sqlite3.IntegrityError:

                    st.error(
                        "A loan with this name already exists."
                    )


# ============================================================
# CARDS + CHEQ
# ============================================================

with tab4:

    st.header("💳 Cards + CheQ")

    total_card_balance = (
        cards["balance"].sum()
        if not cards.empty
        else 0
    )

    st.metric(
        "Total Card Balance",
        money(total_card_balance)
    )

    st.warning(
        "Card rotation is a liquidity bridge. "
        "It does not eliminate the underlying debt."
    )

    if not cards.empty:

        card_display = cards.copy()

        card_display["balance"] = (
            card_display["balance"]
            .apply(money)
        )

        card_display["minimum_due"] = (
            card_display["minimum_due"]
            .apply(money2)
        )

        card_display = card_display.rename(
            columns={
                "name": "Card",
                "balance": "Balance",
                "minimum_due": "Minimum Due",
                "due_date": "Due Date"
            }
        )

        st.dataframe(
            card_display[
                [
                    "Card",
                    "Balance",
                    "Minimum Due",
                    "Due Date"
                ]
            ],
            use_container_width=True,
            hide_index=True
        )

    st.divider()

    st.subheader(
        "🔄 Record Card Rotation"
    )

    if not cards.empty:

        card_name = st.selectbox(
            "Card",
            cards["name"].tolist()
        )

        rotation_amount = st.number_input(
            "Amount rotated",
            min_value=0.0,
            step=1000.0
        )

        rotation_fee = st.number_input(
            "CheQ fee",
            min_value=0.0,
            value=cheq_fee,
            step=100.0
        )

        rotation_date = st.date_input(
            "Date",
            value=date.today()
        )

        if st.button(
            "Record Rotation"
        ):

            if rotation_amount <= 0:

                st.error(
                    "Enter a rotation amount."
                )

            else:

                conn = get_db()
                cur = conn.cursor()

                cur.execute("""
                    INSERT INTO card_rotations
                    (
                        card_name,
                        rotation_date,
                        amount,
                        fee
                    )
                    VALUES (?, ?, ?, ?)
                """, (
                    card_name,
                    str(rotation_date),
                    rotation_amount,
                    rotation_fee
                ))

                conn.commit()
                conn.close()

                st.success(
                    "Rotation recorded."
                )

                st.rerun()

    st.divider()

    st.subheader(
        "📋 Rotation History"
    )

    if rotations.empty:

        st.info(
            "No rotations recorded."
        )

    else:

        rd = rotations.copy()

        rd["amount"] = (
            rd["amount"]
            .apply(money)
        )

        rd["fee"] = (
            rd["fee"]
            .apply(money2)
        )

        st.dataframe(
            rd,
            use_container_width=True,
            hide_index=True
        )

        total_rotated = rotations["amount"].sum()
        total_fees = rotations["fee"].sum()

        c1, c2 = st.columns(2)

        with c1:

            st.metric(
                "Total Rotated",
                money(total_rotated)
            )

        with c2:

            st.metric(
                "Total CheQ Fees",
                money2(total_fees)
            )


# ============================================================
# SETTINGS
# ============================================================

with tab5:

    st.header("⚙️ Settings")

    st.subheader(
        "Income"
    )

    new_salary = st.number_input(
        "Monthly take-home salary",
        min_value=0.0,
        value=salary,
        step=1000.0
    )

    new_bonus = st.number_input(
        "Bonus",
        min_value=0.0,
        value=bonus,
        step=1000.0
    )

    st.subheader(
        "Cash"
    )

    new_cash = st.number_input(
        "Current cash / savings",
        min_value=0.0,
        value=cash,
        step=1000.0
    )

    new_friend = st.number_input(
        "Friend repayment",
        min_value=0.0,
        value=friend_repayment,
        step=1000.0
    )

    st.subheader(
        "CheQ"
    )

    new_cheq_fee = st.number_input(
        "CheQ fee per card",
        min_value=0.0,
        value=cheq_fee,
        step=100.0
    )

    if st.button(
        "💾 Save Settings"
    ):

        save_setting(
            "salary",
            new_salary
        )

        save_setting(
            "bonus",
            new_bonus
        )

        save_setting(
            "cash",
            new_cash
        )

        save_setting(
            "friend_repayment",
            new_friend
        )

        save_setting(
            "cheq_fee",
            new_cheq_fee
        )

        st.success(
            "Settings saved."
        )

        st.rerun()

    st.divider()

    st.subheader(
        "📈 Salary Scenario"
    )

    increment = st.number_input(
        "Expected increment %",
        min_value=0.0,
        max_value=100.0,
        value=10.0,
        step=1.0
    )

    projected_salary = (
        salary
        * (1 + increment / 100)
    )

    st.metric(
        "Salary After Increment",
        money(projected_salary)
    )

    st.caption(
        "This is only a scenario and does not change your current salary."
    )

    st.divider()

    st.subheader(
        "Current Assumptions"
    )

    assumptions = pd.DataFrame(
        [
            ["Forecast Start", "26 Sep 2026"],
            ["First Forecast Month", "October 2026"],
            ["Salary", money(salary)],
            ["Living Expenses", money(living_total)],
            ["Current Cash", money(cash)],
            ["Bonus", money(bonus)],
            ["Friend Repayment", money(friend_repayment)],
            [
                "Cash After Friend",
                money(
                    cash
                    + bonus
                    - friend_repayment
                )
            ],
            ["CheQ Fee", money(cheq_fee)],
        ],
        columns=[
            "Item",
            "Value"
        ]
    )

    st.table(
        assumptions
    )

    st.divider()

    st.subheader(
        "🗑️ Reset App"
    )

    st.warning(
        "This will delete your saved changes and restore the original loan/card numbers."
    )

    if st.button(
        "Reset All Data"
    ):

        try:

            conn = get_db()
            cur = conn.cursor()

            tables = [
                "loans",
                "cards",
                "payments",
                "foreclosures",
                "card_rotations",
                "expenses",
                "settings"
            ]

            for table in tables:

                cur.execute(
                    f"DELETE FROM {table}"
                )

            conn.commit()
            conn.close()

            # Recreate defaults
            setup_database()

            save_setting(
                "salary",
                DEFAULT_SALARY
            )

            save_setting(
                "bonus",
                DEFAULT_BONUS
            )

            save_setting(
                "cash",
                DEFAULT_CASH
            )

            save_setting(
                "friend_repayment",
                DEFAULT_FRIEND_REPAYMENT
            )

            save_setting(
                "cheq_fee",
                DEFAULT_CHEQ_FEE
            )

            st.success(
                "Everything has been reset."
            )

            st.rerun()

        except Exception as e:

            st.error(
                f"Could not reset database: {e}"
            )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "Debt Command Center | Starting point: 26 Sep 2026 | "
    "September EMIs already paid | Forecast begins October 2026"
)
