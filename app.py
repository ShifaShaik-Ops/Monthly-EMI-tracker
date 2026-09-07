import streamlit as st
import sqlite3
import pandas as pd
from datetime import date
import calendar

# ============================================================
# PAGE
# ============================================================

st.set_page_config(
    page_title="Debt Command Center",
    page_icon="💰",
    layout="wide",
)

# ============================================================
# CONSTANTS
# ============================================================

DB_FILE = "debt_manager.db"

FORECAST_START_YEAR = 2026
FORECAST_START_MONTH = 10

SALARY_DEFAULT = 59000
BONUS_DEFAULT = 60000
CASH_DEFAULT = 40000
FRIEND_REPAYMENT_DEFAULT = 80000
CHEQ_FEE_DEFAULT = 2000

LIVING_EXPENSES = {
    "Rent": 15000,
    "Fuel": 2000,
    "Grocery": 2000,
    "Miscellaneous": 2000,
    "JioFiber": 1200,
    "Salon": 2000,
}

DEFAULT_LOANS = [
    ["Fibe", 9890, 6, 4, "₹9,890 EMI"],
    ["Stashfin", 4199, 11, 2, "Rotatable only if needed"],
    ["Kredibee", 9219, 5, 2, ""],
    ["Branch", 2488, 4, 28, ""],
    ["Money View", 3764, 5, 3, ""],
    ["Poonawala Fincorp", 6507, 21, 5, ""],
    ["Instamoney", 5616, 2, 1, "Rotatable only if needed"],
    ["Kissht", 1583, 8, 7, ""],
    ["Loan Tap", 5276, 1, 1, ""],
    ["Flexipay", 6000, 23, 26, ""],
]

DEFAULT_CARDS = [
    ["Axis", 60000, 0, ""],
    ["HDFC", 29656, 1816, "2026-08-28"],
    ["DBS", 36000, 1089.79, "2026-09-01"],
]

# ============================================================
# HELPERS
# ============================================================

def money(x):
    try:
        x = float(x or 0)
    except (TypeError, ValueError):
        x = 0.0

    sign = "-" if x < 0 else ""
    x = abs(x)

    return f"{sign}₹{x:,.0f}"


def money2(x):
    try:
        x = float(x or 0)
    except (TypeError, ValueError):
        x = 0.0

    return f"₹{x:,.2f}"


def add_months(year, month, number):
    total = year * 12 + (month - 1) + number
    new_year = total // 12
    new_month = total % 12 + 1
    return new_year, new_month


def month_name(year, month):
    return f"{calendar.month_name[month]} {year}"


# ============================================================
# DATABASE
# ============================================================

def db():
    return sqlite3.connect(DB_FILE, check_same_thread=False)


def initialize_database():
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
            emi REAL NOT NULL,
            months_left INTEGER NOT NULL,
            emi_date INTEGER,
            notes TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            balance REAL NOT NULL,
            minimum_due REAL DEFAULT 0,
            due_date TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT,
            amount REAL,
            expense_date TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            loan_id INTEGER,
            payment_date TEXT,
            amount REAL,
            note TEXT
        )
    """)

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

    cur.execute("""
        CREATE TABLE IF NOT EXISTS card_rotations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            card_name TEXT,
            rotation_date TEXT,
            amount REAL,
            fee REAL
        )
    """)

    conn.commit()
    conn.close()


initialize_database()


# ============================================================
# SETTINGS
# ============================================================

def get_setting(key, default):
    conn = db()
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
    conn = db()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO settings(key, value)
        VALUES (?, ?)
        ON CONFLICT(key)
        DO UPDATE SET value=excluded.value
    """, (key, str(value)))

    conn.commit()
    conn.close()


# ============================================================
# SEED
# ============================================================

def seed_database():

    conn = db()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM loans")
    loan_count = cur.fetchone()[0]

    if loan_count == 0:
        for loan in DEFAULT_LOANS:
            cur.execute("""
                INSERT INTO loans
                (name, emi, months_left, emi_date, notes)
                VALUES (?, ?, ?, ?, ?)
            """, loan)

    cur.execute("SELECT COUNT(*) FROM cards")
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

    defaults = {
        "salary": SALARY_DEFAULT,
        "bonus": BONUS_DEFAULT,
        "cash": CASH_DEFAULT,
        "friend_repayment": FRIEND_REPAYMENT_DEFAULT,
        "cheq_fee": CHEQ_FEE_DEFAULT,
    }

    for key, value in defaults.items():
        if get_setting(key, None) is None:
            save_setting(key, value)


seed_database()


# ============================================================
# LOAD DATA
# ============================================================

def load_loans():
    conn = db()

    df = pd.read_sql_query(
        """
        SELECT *
        FROM loans
        ORDER BY name
        """,
        conn
    )

    conn.close()
    return df


def load_cards():
    conn = db()

    df = pd.read_sql_query(
        """
        SELECT *
        FROM cards
        ORDER BY name
        """,
        conn
    )

    conn.close()
    return df


def load_payments():
    conn = db()

    df = pd.read_sql_query(
        """
        SELECT *
        FROM payments
        ORDER BY payment_date DESC
        """,
        conn
    )

    conn.close()
    return df


def load_foreclosures():
    conn = db()

    df = pd.read_sql_query(
        """
        SELECT
            f.id,
            f.loan_id,
            l.name AS loan_name,
            l.emi,
            l.months_left,
            f.quote_date,
            f.foreclosure_amount,
            f.valid_until,
            f.note
        FROM foreclosures f
        JOIN loans l
        ON l.id = f.loan_id
        ORDER BY f.quote_date DESC
        """,
        conn
    )

    conn.close()
    return df


def load_rotations():
    conn = db()

    df = pd.read_sql_query(
        """
        SELECT *
        FROM card_rotations
        ORDER BY rotation_date DESC
        """,
        conn
    )

    conn.close()
    return df


# ============================================================
# CURRENT VALUES
# ============================================================

salary = float(get_setting("salary", SALARY_DEFAULT))
bonus = float(get_setting("bonus", BONUS_DEFAULT))
cash = float(get_setting("cash", CASH_DEFAULT))
friend_repayment = float(
    get_setting(
        "friend_repayment",
        FRIEND_REPAYMENT_DEFAULT
    )
)
cheq_fee = float(get_setting("cheq_fee", CHEQ_FEE_DEFAULT))

loans = load_loans()
cards = load_cards()
payments = load_payments()
foreclosures = load_foreclosures()
rotations = load_rotations()

living_total = sum(LIVING_EXPENSES.values())


# ============================================================
# FORECAST ENGINE
# ============================================================

def build_forecast(number_of_months=24):

    rows = []

    for i in range(number_of_months):

        year, month = add_months(
            FORECAST_START_YEAR,
            FORECAST_START_MONTH,
            i
        )

        emi_total = 0
        active_loans = 0
        details = []

        for _, loan in loans.iterrows():

            remaining = max(
                0,
                int(loan["months_left"]) - i
            )

            if remaining > 0:

                emi_total += float(loan["emi"])
                active_loans += 1

                details.append({
                    "name": loan["name"],
                    "emi": float(loan["emi"]),
                    "months_left": remaining,
                })

        monthly_cash_flow = (
            salary
            - living_total
            - emi_total
        )

        rows.append({
            "year": year,
            "month": month,
            "label": month_name(year, month),
            "salary": salary,
            "living": living_total,
            "emi": emi_total,
            "cash_flow": monthly_cash_flow,
            "active_loans": active_loans,
            "details": details,
        })

    return pd.DataFrame(rows)


forecast = build_forecast()


# ============================================================
# HEADER
# ============================================================

st.title("💰 Debt Command Center")

st.caption(
    "Your goal: survive the EMI bridge, stop new borrowing, "
    "then aggressively eliminate revolving debt."
)

st.info(
    "📅 Starting point: 26 September 2026. "
    "September EMIs are already paid. Forecast begins October 2026."
)


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.header("Current Situation")

    st.metric(
        "Salary",
        money(salary)
    )

    st.metric(
        "Living Expenses",
        money(living_total)
    )

    st.metric(
        "Current EMI",
        money(
            loans["emi"].sum()
            if not loans.empty else 0
        )
    )

    st.divider()

    st.write("**Forecast starts:**")
    st.write("26 Sep 2026")

    st.write("**First forecast:**")
    st.write("October 2026")


# ============================================================
# TABS
# ============================================================

tab_command, tab_forecast, tab_loans, tab_cards, tab_expenses, tab_settings = st.tabs(
    [
        "🚨 Command Center",
        "📊 Forecast",
        "🏦 Loans",
        "💳 Cards + CheQ",
        "💸 Expenses",
        "⚙️ Settings",
    ]
)


# ============================================================
# COMMAND CENTER
# ============================================================

with tab_command:

    st.header("🚨 NO NEW LOAN PLAN")

    # --------------------------------------------------------
    # CASH POSITION
    # --------------------------------------------------------

    cash_after_friend = (
        cash
        + bonus
        - friend_repayment
    )

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Current Cash",
            money(cash)
        )

    with col2:
        st.metric(
            "Bonus",
            money(bonus)
        )

    with col3:
        st.metric(
            "Friend Repayment",
            money(friend_repayment)
        )

    with col4:
        st.metric(
            "Cash After Friend",
            money(cash_after_friend)
        )

    # --------------------------------------------------------
    # CURRENT MONTHLY POSITION
    # --------------------------------------------------------

    current_emi = (
        loans["emi"].sum()
        if not loans.empty else 0
    )

    current_cash_flow = (
        salary
        - living_total
        - current_emi
    )

    st.subheader("1️⃣ Monthly reality")

    a, b, c, d = st.columns(4)

    with a:
        st.metric("Salary", money(salary))

    with b:
        st.metric("Living", money(living_total))

    with c:
        st.metric("EMIs", money(current_emi))

    with d:
        st.metric(
            "Monthly Cash Flow",
            money(current_cash_flow)
        )

    if current_cash_flow < 0:

        st.error(
            f"🚨 You are structurally short by "
            f"**{money(abs(current_cash_flow))} per month**."
        )

    else:

        st.success(
            f"Monthly surplus: **{money(current_cash_flow)}**"
        )

    # --------------------------------------------------------
    # BRIDGE ANALYSIS
    # --------------------------------------------------------

    st.subheader("2️⃣ How much do you need to survive the bridge?")

    cumulative = 0
    worst_point = 0
    worst_month = None

    bridge_rows = []

    for _, row in forecast.head(12).iterrows():

        cumulative += row["cash_flow"]

        if cumulative < worst_point:
            worst_point = cumulative
            worst_month = row["label"]

        bridge_rows.append({
            "Month": row["label"],
            "EMI": row["emi"],
            "Monthly Cash Flow": row["cash_flow"],
            "Cumulative Cash Flow": cumulative,
        })

    bridge_df = pd.DataFrame(bridge_rows)

    required_bridge = abs(min(0, worst_point))

    if required_bridge > 0:

        st.warning(
            f"Estimated maximum cash-flow gap before recovery: "
            f"**{money(required_bridge)}**."
        )

        if cash_after_friend >= required_bridge:

            st.success(
                f"Your post-friend cash of {money(cash_after_friend)} "
                f"can cover this modeled bridge."
            )

        else:

            gap = (
                required_bridge
                - cash_after_friend
            )

            st.error(
                f"You may still need approximately "
                f"**{money(gap)}** of additional bridge funding."
            )

    # --------------------------------------------------------
    # FIRST POSITIVE MONTH
    # --------------------------------------------------------

    positive_month = None

    for _, row in forecast.iterrows():

        if row["cash_flow"] >= 0:

            positive_month = row["label"]
            break

    if positive_month:

        st.success(
            f"🎯 Monthly cash flow first becomes positive around "
            f"**{positive_month}**."
        )

    # --------------------------------------------------------
    # MONTHLY TABLE
    # --------------------------------------------------------

    display_bridge = bridge_df.copy()

    for col in [
        "EMI",
        "Monthly Cash Flow",
        "Cumulative Cash Flow",
    ]:
        display_bridge[col] = display_bridge[col].apply(money)

    st.dataframe(
        display_bridge,
        use_container_width=True,
        hide_index=True
    )

    # --------------------------------------------------------
    # ACTION PLAN
    # --------------------------------------------------------

    st.subheader("3️⃣ Recommended strategy")

    if current_cash_flow < 0:

        st.markdown("""
        **Phase 1 — October to the recovery month**

        1. Do **not** take another loan just to cover a temporary EMI gap.
        2. Keep enough cash available for the next EMIs.
        3. Reduce unnecessary spending before rotating additional cards.
        4. If card rotation is unavoidable, rotate only the amount actually required.
        5. Do not aggressively foreclose a loan if doing so destroys your bridge cash.
        6. Get actual foreclosure quotes before deciding which EMI to close.
        """)

    else:

        st.markdown("""
        **Phase 1 — Positive cash-flow mode**

        1. Stop unnecessary card rotation.
        2. Attack the highest-cost revolving debt.
        3. When an EMI disappears, redirect the freed EMI toward debt.
        4. Avoid lifestyle inflation.
        """)

    # --------------------------------------------------------
    # FORECLOSURE DECISION ENGINE
    # --------------------------------------------------------

    st.divider()

    st.subheader("4️⃣ 🏦 Should I close an EMI early?")

    st.write(
        "Enter an **actual lender foreclosure quote**. "
        "The app will compare how much monthly EMI you remove "
        "against how much cash you spend."
    )

    if loans.empty:

        st.info("No loans available.")

    else:

        active = loans[
            loans["months_left"] > 0
        ].copy()

        if not active.empty:

            loan_choice = st.selectbox(
                "Loan to evaluate",
                active["name"].tolist()
            )

            loan = active[
                active["name"] == loan_choice
            ].iloc[0]

            c1, c2, c3 = st.columns(3)

            with c1:
                st.metric(
                    "EMI Freed",
                    money(loan["emi"])
                )

            with c2:
                st.metric(
                    "Months Left",
                    int(loan["months_left"])
                )

            with c3:
                st.metric(
                    "Scheduled Remaining",
                    money(
                        loan["emi"]
                        * loan["months_left"]
                    )
                )

            quote = st.number_input(
                "Actual foreclosure amount",
                min_value=0.0,
                step=1000.0,
                value=0.0
            )

            if quote > 0:

                remaining_cash = (
                    cash_after_friend
                    - quote
                )

                efficiency = (
                    loan["emi"]
                    / quote
                )

                st.write(
                    f"Cash after foreclosure: "
                    f"**{money(remaining_cash)}**"
                )

                st.write(
                    f"Monthly EMI reduction: "
                    f"**{money(loan['emi'])}**"
                )

                st.write(
                    f"Cash-flow efficiency: "
                    f"**{efficiency:.4f} EMI/₹**"
                )

                if remaining_cash < required_bridge:

                    st.error(
                        "❌ Not recommended right now. "
                        "This foreclosure would leave you with less "
                        "cash than the modeled bridge requirement."
                    )

                else:

                    improved_flow = (
                        current_cash_flow
                        + loan["emi"]
                    )

                    st.success(
                        f"After closing this loan, monthly cash flow "
                        f"would improve by {money(loan['emi'])}."
                    )

                    st.write(
                        f"Estimated new monthly cash flow: "
                        f"**{money(improved_flow)}**"
                    )

                    if improved_flow >= 0:

                        st.success(
                            "🎯 This foreclosure could eliminate the "
                            "current monthly structural deficit."
                        )

                    else:

                        st.warning(
                            "This foreclosure helps but does not "
                            "eliminate the monthly deficit."
                        )

                    if st.button(
                        "Save this foreclosure quote",
                        key=f"save_quote_{loan['id']}"
                    ):

                        conn = db()
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
                            int(loan["id"]),
                            str(date.today()),
                            quote,
                            "",
                            "Entered from Command Center"
                        ))

                        conn.commit()
                        conn.close()

                        st.success(
                            "Foreclosure quote saved."
                        )

                        st.rerun()

    # --------------------------------------------------------
    # CARD DECISION
    # --------------------------------------------------------

    st.divider()

    st.subheader("5️⃣ 💳 How much card rotation should I use?")

    shortage_to_bridge = st.number_input(
        "Actual amount you need to bridge this month",
        min_value=0.0,
        step=1000.0,
        value=float(
            max(
                0,
                -current_cash_flow
            )
        )
    )

    if shortage_to_bridge <= 0:

        st.success(
            "No card rotation is needed based on the current basic budget."
        )

    else:

        cards_needed = 0

        if not cards.empty:

            remaining = shortage_to_bridge

            for _, card in cards.iterrows():

                if remaining > 0:

                    cards_needed += 1
                    remaining -= float(card["balance"])

        estimated_fee = (
            cards_needed
            * cheq_fee
        )

        st.write(
            f"Estimated cards needed: **{cards_needed}**"
        )

        st.write(
            f"Estimated CheQ cost: **{money(estimated_fee)}**"
        )

        st.warning(
            "Use the minimum number of cards and minimum amount "
            "necessary. Card rotation is a bridge, not debt repayment."
        )

    # --------------------------------------------------------
    # NEW LOAN TEST
    # --------------------------------------------------------

    st.divider()

    st.subheader("6️⃣ 🚫 New Loan Test")

    new_loan_emi = st.number_input(
        "If I take a new loan, what will the EMI be?",
        min_value=0.0,
        step=500.0,
        value=0.0
    )

    if new_loan_emi > 0:

        new_flow = (
            current_cash_flow
            - new_loan_emi
        )

        st.write(
            f"Current monthly cash flow: "
            f"**{money(current_cash_flow)}**"
        )

        st.write(
            f"After new EMI: "
            f"**{money(new_flow)}**"
        )

        if current_cash_flow < 0:

            st.error(
                "🚨 You are already running a deficit. "
                "A new EMI makes the structural problem worse."
            )

        elif new_flow < 0:

            st.warning(
                "The new loan would push your monthly cash flow "
                "back into deficit."
            )

        else:

            st.info(
                "The new EMI does not create a negative monthly "
                "cash flow under the current assumptions, but "
                "check total repayment and fees."
            )


# ============================================================
# FORECAST TAB
# ============================================================

with tab_forecast:

    st.header("📊 EMI Forecast")

    show = forecast.drop(
        columns=["details"]
    ).copy()

    show = show.rename(
        columns={
            "label": "Month",
            "salary": "Salary",
            "living": "Living Expenses",
            "emi": "EMIs",
            "cash_flow": "Monthly Cash Flow",
            "active_loans": "Active Loans",
        }
    )

    for col in [
        "Salary",
        "Living Expenses",
        "EMIs",
        "Monthly Cash Flow",
    ]:
        show[col] = show[col].apply(money)

    st.dataframe(
        show[
            [
                "Month",
                "Salary",
                "Living Expenses",
                "EMIs",
                "Monthly Cash Flow",
                "Active Loans",
            ]
        ],
        use_container_width=True,
        hide_index=True
    )

    st.subheader("EMI trend")

    chart = forecast[
        ["label", "emi"]
    ].copy()

    chart = chart.set_index("label")

    st.line_chart(chart)

    st.subheader("Cash-flow trend")

    cash_chart = forecast[
        ["label", "cash_flow"]
    ].copy()

    cash_chart = cash_chart.set_index("label")

    st.line_chart(cash_chart)


# ============================================================
# LOANS TAB
# ============================================================

with tab_loans:

    st.header("🏦 Loans")

    if loans.empty:

        st.info("No loans.")

    else:

        display = loans.copy()

        display["emi"] = display["emi"].apply(money)

        display = display.rename(
            columns={
                "name": "Loan",
                "emi": "EMI",
                "months_left": "Months Left",
                "emi_date": "EMI Date",
                "notes": "Notes",
            }
        )

        st.dataframe(
            display[
                [
                    "Loan",
                    "EMI",
                    "Months Left",
                    "EMI Date",
                    "Notes",
                ]
            ],
            use_container_width=True,
            hide_index=True
        )

    st.divider()

    st.subheader("➕ Add Loan")

    with st.form("add_loan"):

        new_name = st.text_input("Loan name")

        new_emi = st.number_input(
            "EMI",
            min_value=0.0,
            step=100.0
        )

        new_months = st.number_input(
            "Remaining months",
            min_value=0,
            step=1
        )

        new_date = st.number_input(
            "EMI date",
            min_value=1,
            max_value=31,
            value=1,
            step=1
        )

        new_notes = st.text_input("Notes")

        submitted = st.form_submit_button(
            "Add Loan"
        )

        if submitted:

            if not new_name.strip():

                st.error("Enter a loan name.")

            elif new_emi <= 0:

                st.error("Enter a valid EMI.")

            else:

                try:

                    conn = db()
                    cur = conn.cursor()

                    cur.execute("""
                        INSERT INTO loans
                        (name, emi, months_left, emi_date, notes)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        new_name.strip(),
                        new_emi,
                        int(new_months),
                        int(new_date),
                        new_notes
                    ))

                    conn.commit()
                    conn.close()

                    st.success("Loan added.")
                    st.rerun()

                except sqlite3.IntegrityError:

                    st.error(
                        "A loan with this name already exists."
                    )

    st.divider()

    st.subheader("✏️ Update Loan")

    if not loans.empty:

        selected_id = st.selectbox(
            "Select loan",
            loans["id"].tolist(),
            format_func=lambda x:
                loans.loc[
                    loans["id"] == x,
                    "name"
                ].iloc[0]
        )

        selected = loans[
            loans["id"] == selected_id
        ].iloc[0]

        updated_months = st.number_input(
            "Months remaining",
            min_value=0,
            max_value=120,
            value=int(selected["months_left"]),
            step=1
        )

        updated_emi = st.number_input(
            "EMI",
            min_value=0.0,
            value=float(selected["emi"]),
            step=100.0
        )

        if st.button("Save Loan Changes"):

            conn = db()
            cur = conn.cursor()

            cur.execute("""
                UPDATE loans
                SET months_left=?, emi=?
                WHERE id=?
            """, (
                int(updated_months),
                updated_emi,
                int(selected_id)
            ))

            conn.commit()
            conn.close()

            st.success("Loan updated.")
            st.rerun()

    st.divider()

    st.subheader("💰 Record EMI Payment")

    if not loans.empty:

        payment_id = st.selectbox(
            "Loan",
            loans["id"].tolist(),
            format_func=lambda x:
                loans.loc[
                    loans["id"] == x,
                    "name"
                ].iloc[0],
            key="payment_loan"
        )

        payment_loan = loans[
            loans["id"] == payment_id
        ].iloc[0]

        payment_amount = st.number_input(
            "Payment amount",
            min_value=0.0,
            value=float(payment_loan["emi"]),
            step=100.0
        )

        payment_day = st.date_input(
            "Payment date",
            value=date.today()
        )

        payment_note = st.text_input(
            "Payment note"
        )

        if st.button(
            "Record Payment"
        ):

            conn = db()
            cur = conn.cursor()

            cur.execute("""
                INSERT INTO payments
                (loan_id, payment_date, amount, note)
                VALUES (?, ?, ?, ?)
            """, (
                int(payment_id),
                str(payment_day),
                payment_amount,
                payment_note
            ))

            # Only reduce months if there are months left.
            new_months = max(
                0,
                int(payment_loan["months_left"]) - 1
            )

            cur.execute("""
                UPDATE loans
                SET months_left=?
                WHERE id=?
            """, (
                new_months,
                int(payment_id)
            ))

            conn.commit()
            conn.close()

            st.success(
                f"Payment recorded for {payment_loan['name']}."
            )

            st.rerun()

    st.divider()

    st.subheader("📋 Saved Foreclosure Quotes")

    if not foreclosures.empty:

        fd = foreclosures.copy()

        fd["foreclosure_amount"] = fd[
            "foreclosure_amount"
        ].apply(money)

        fd["emi"] = fd["emi"].apply(money)

        fd["monthly_reduction_per_rupee"] = (
            foreclosures["emi"]
            / foreclosures["foreclosure_amount"]
        ).round(5)

        st.dataframe(
            fd[
                [
                    "loan_name",
                    "emi",
                    "months_left",
                    "quote_date",
                    "foreclosure_amount",
                    "monthly_reduction_per_rupee",
                ]
            ],
            use_container_width=True,
            hide_index=True
        )

    else:

        st.info(
            "No foreclosure quotes saved yet."
        )


# ============================================================
# CARDS TAB
# ============================================================

with tab_cards:

    st.header("💳 Credit Cards + CheQ")

    total_cards = (
        cards["balance"].sum()
        if not cards.empty else 0
    )

    st.metric(
        "Total Card Balance",
        money(total_cards)
    )

    st.warning(
        "CheQ rotation provides liquidity but does not remove "
        "the underlying card debt. Fees must be treated as a real cost."
    )

    if not cards.empty:

        cd = cards.copy()

        cd["balance"] = cd["balance"].apply(money)
        cd["minimum_due"] = cd["minimum_due"].apply(money2)

        cd = cd.rename(
            columns={
                "name": "Card",
                "balance": "Balance",
                "minimum_due": "Minimum Due",
                "due_date": "Due Date",
            }
        )

        st.dataframe(
            cd[
                [
                    "Card",
                    "Balance",
                    "Minimum Due",
                    "Due Date",
                ]
            ],
            use_container_width=True,
            hide_index=True
        )

    st.divider()

    st.subheader("🔄 Record CheQ Rotation")

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
            value=float(cheq_fee),
            step=100.0
        )

        rotation_date = st.date_input(
            "Rotation date",
            value=date.today()
        )

        if st.button("Record Rotation"):

            if rotation_amount <= 0:

                st.error(
                    "Enter the amount rotated."
                )

            else:

                conn = db()
                cur = conn.cursor()

                cur.execute("""
                    INSERT INTO card_rotations
                    (card_name, rotation_date, amount, fee)
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

    st.subheader("📋 Rotation History")

    if not rotations.empty:

        rd = rotations.copy()

        rd["amount"] = rd["amount"].apply(money)
        rd["fee"] = rd["fee"].apply(money2)

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

    else:

        st.info(
            "No rotations recorded."
        )


# ============================================================
# EXPENSES TAB
# ============================================================

with tab_expenses:

    st.header("💸 Expenses")

    expense_data = pd.DataFrame(
        [
            {
                "Category": category,
                "Monthly Amount": amount
            }
            for category, amount in LIVING_EXPENSES.items()
        ]
    )

    expense_data["Monthly Amount"] = (
        expense_data["Monthly Amount"]
        .apply(money)
    )

    st.dataframe(
        expense_data,
        use_container_width=True,
        hide_index=True
    )

    st.metric(
        "Total Monthly Living",
        money(living_total)
    )

    st.divider()

    st.subheader("➕ Record Actual Expense")

    with st.form("expense_form"):

        expense_category = st.text_input(
            "Category"
        )

        expense_amount = st.number_input(
            "Amount",
            min_value=0.0,
            step=100.0
        )

        expense_date = st.date_input(
            "Date",
            value=date.today()
        )

        add_expense = st.form_submit_button(
            "Save Expense"
        )

        if add_expense:

            if expense_amount <= 0:

                st.error(
                    "Enter a valid amount."
                )

            else:

                conn = db()
                cur = conn.cursor()

                cur.execute("""
                    INSERT INTO expenses
                    (category, amount, expense_date)
                    VALUES (?, ?, ?)
                """, (
                    expense_category,
                    expense_amount,
                    str(expense_date)
                ))

                conn.commit()
                conn.close()

                st.success(
                    "Expense saved."
                )

                st.rerun()


# ============================================================
# SETTINGS TAB
# ============================================================

with tab_settings:

    st.header("⚙️ Settings")

    st.subheader("Income")

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

    st.subheader("Cash")

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

    st.subheader("CheQ")

    new_fee = st.number_input(
        "CheQ fee per card",
        min_value=0.0,
        value=cheq_fee,
        step=100.0
    )

    if st.button("💾 Save Settings"):

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
            new_fee
        )

        st.success(
            "Settings saved successfully."
        )

        st.rerun()

    st.divider()

    st.subheader("📈 Expected Salary Increase")

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
        "Projected Salary",
        money(projected_salary)
    )

    st.caption(
        "This is only a planning scenario and does not change "
        "your actual salary."
    )

    st.divider()

    st.subheader("Current assumptions")

    assumptions = pd.DataFrame(
        [
            ["Forecast start", "26 Sep 2026"],
            ["First forecast month", "October 2026"],
            ["Salary", money(salary)],
            ["Living expenses", money(living_total)],
            ["Current cash", money(cash)],
            ["Bonus", money(bonus)],
            ["Friend repayment", money(friend_repayment)],
            ["Cash after friend", money(cash + bonus - friend_repayment)],
            ["CheQ fee/card", money(cheq_fee)],
        ],
        columns=["Item", "Value"]
    )

    st.table(assumptions)

    st.divider()

    st.subheader("🗑️ Reset Database")

    st.warning(
        "Only use this if you want to completely reset the app "
        "back to the original numbers."
    )

    if st.button("Reset Database"):

        conn = db()
        cur = conn.cursor()

        cur.execute("DELETE FROM loans")
        cur.execute("DELETE FROM cards")
        cur.execute("DELETE FROM settings")
        cur.execute("DELETE FROM payments")
        cur.execute("DELETE FROM foreclosures")
        cur.execute("DELETE FROM card_rotations")
        cur.execute("DELETE FROM expenses")

        conn.commit()
        conn.close()

        seed_database()

        st.success(
            "Database reset to default values."
        )

        st.rerun()


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "Debt Command Center • Forecast begins October 2026 • "
    "Actual foreclosure quotes should come from the lender."
)
