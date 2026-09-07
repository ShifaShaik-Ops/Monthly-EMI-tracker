import streamlit as st
import sqlite3
from datetime import date
from pathlib import Path
import pandas as pd

# ============================================================
# APP CONFIG
# ============================================================

st.set_page_config(
    page_title="Debt Manager",
    page_icon="💰",
    layout="wide",
)

APP_DIR = Path(__file__).parent
DB_PATH = APP_DIR / "debt_manager.db"


# ============================================================
# HELPERS
# ============================================================

def money(value):
    """Format Indian Rupees without scientific notation."""
    if value is None:
        value = 0

    try:
        value = float(value)
    except:
        value = 0

    sign = "-" if value < 0 else ""
    value = abs(value)

    # Indian number formatting
    number = f"{value:,.0f}"

    return f"{sign}₹{number}"


def db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():

    conn = db()
    c = conn.cursor()

    # -----------------------------
    # SETTINGS
    # -----------------------------

    c.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value REAL
        )
    """)

    # -----------------------------
    # LOANS
    # -----------------------------

    c.execute("""
        CREATE TABLE IF NOT EXISTS loans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            emi REAL,
            pending_months INTEGER,
            emi_day INTEGER,
            rotatable INTEGER DEFAULT 0,
            active INTEGER DEFAULT 1
        )
    """)

    # -----------------------------
    # CREDIT CARDS
    # -----------------------------

    c.execute("""
        CREATE TABLE IF NOT EXISTS cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            balance REAL,
            min_due REAL,
            due_day INTEGER,
            active INTEGER DEFAULT 1
        )
    """)

    # -----------------------------
    # EXPENSES
    # -----------------------------

    c.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            txn_date TEXT,
            category TEXT,
            amount REAL,
            kind TEXT,
            note TEXT
        )
    """)

    # -----------------------------
    # LOAN PAYMENTS
    # -----------------------------

    c.execute("""
        CREATE TABLE IF NOT EXISTS loan_payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            loan_id INTEGER,
            pay_date TEXT,
            amount REAL,
            months_reduced INTEGER,
            note TEXT
        )
    """)

    # -----------------------------
    # CARD / CHEQ CYCLES
    # -----------------------------

    c.execute("""
        CREATE TABLE IF NOT EXISTS card_cycles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            card_id INTEGER,
            cycle_date TEXT,
            paid_amount REAL,
            recycled_amount REAL,
            cheq_fee REAL,
            note TEXT
        )
    """)

    # -----------------------------
    # NEW DEBTS
    # -----------------------------

    c.execute("""
        CREATE TABLE IF NOT EXISTS new_debts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            debt_date TEXT,
            lender TEXT,
            amount REAL,
            monthly_payment REAL,
            months INTEGER,
            note TEXT
        )
    """)

    # ========================================================
    # DEFAULT SETTINGS
    # ========================================================

    defaults = {

        "salary": 59000,

        "annual_salary": 723256,

        "increment_pct": 10,

        "bonus": 60000,

        "savings": 40000,

        "friend_loan": 80000,

        # Living expenses
        "rent": 15000,
        "fuel": 2000,
        "groceries": 2000,
        "misc": 2000,
        "jio": 1200,
        "salon": 2000,

        # CheQ
        "cheq_fee_per_card": 2000,

        # Minimum cash buffer
        "emergency_buffer": 10000,
    }

    for key, value in defaults.items():

        c.execute(
            """
            INSERT OR IGNORE INTO settings(key,value)
            VALUES (?,?)
            """,
            (key, value),
        )

    # ========================================================
    # LOANS
    # ========================================================

    loans = [

        ("Fibe", 9890, 7, 4, 0),

        ("Stashfin", 4199, 12, 2, 1),

        ("LazyPay", 4000, 1, 3, 1),

        ("Kredibee", 9219, 6, 2, 0),

        ("Branch", 2488, 5, 28, 0),

        ("Money View", 3764, 6, 3, 0),

        ("Poonawala Fincorp", 6507, 22, 5, 0),

        ("Instamoney", 5616, 3, 1, 1),

        ("Kissht", 1583, 9, 7, 0),

        ("Loan Tap", 5276, 2, 1, 0),

        ("Flexipay", 6000, 24, 26, 0),

    ]

    for loan in loans:

        c.execute(
            """
            INSERT OR IGNORE INTO loans
            (name,emi,pending_months,emi_day,rotatable)
            VALUES (?,?,?,?,?)
            """,
            loan,
        )

    # ========================================================
    # CREDIT CARDS
    # ========================================================

    cards = [

        # Axis minimum is only an estimate.
        ("Axis", 60000, 2000, 0),

        # From statement supplied.
        ("HDFC", 29656, 1816, 28),

        # Use 36k as user's stated balance.
        ("DBS", 36000, 1089.79, 1),

    ]

    for card in cards:

        c.execute(
            """
            INSERT OR IGNORE INTO cards
            (name,balance,min_due,due_day)
            VALUES (?,?,?,?)
            """,
            card,
        )

    conn.commit()
    conn.close()


# ============================================================
# DATABASE FUNCTIONS
# ============================================================

def get_settings():

    conn = db()

    rows = conn.execute(
        "SELECT key,value FROM settings"
    ).fetchall()

    conn.close()

    return {
        row["key"]: row["value"]
        for row in rows
    }


def set_setting(key, value):

    conn = db()

    conn.execute(
        """
        INSERT OR REPLACE INTO settings(key,value)
        VALUES (?,?)
        """,
        (key, float(value)),
    )

    conn.commit()
    conn.close()


def loans_df():

    conn = db()

    df = pd.read_sql_query(
        """
        SELECT *
        FROM loans
        ORDER BY pending_months ASC
        """,
        conn,
    )

    conn.close()

    return df


def cards_df():

    conn = db()

    df = pd.read_sql_query(
        """
        SELECT *
        FROM cards
        ORDER BY balance DESC
        """,
        conn,
    )

    conn.close()

    return df


def payments_df():

    conn = db()

    df = pd.read_sql_query(
        """
        SELECT
            lp.*,
            l.name
        FROM loan_payments lp
        LEFT JOIN loans l
        ON l.id = lp.loan_id
        ORDER BY pay_date DESC
        """,
        conn,
    )

    conn.close()

    return df


def card_cycles_df():

    conn = db()

    df = pd.read_sql_query(
        """
        SELECT
            cc.*,
            c.name
        FROM card_cycles cc
        LEFT JOIN cards c
        ON c.id = cc.card_id
        ORDER BY cycle_date DESC
        """,
        conn,
    )

    conn.close()

    return df


def expenses_df():

    conn = db()

    df = pd.read_sql_query(
        """
        SELECT *
        FROM transactions
        ORDER BY txn_date DESC
        """,
        conn,
    )

    conn.close()

    return df


# ============================================================
# INITIALIZE
# ============================================================

init_db()

today = date.today()


# ============================================================
# SIDEBAR
# ============================================================

settings = get_settings()

st.sidebar.title("⚙️ Your Financial Controls")

st.sidebar.caption(
    "Change your real numbers here. "
    "The recommendations update automatically."
)


# ============================================================
# INCOME
# ============================================================

with st.sidebar.expander(
    "💰 Income & Cash",
    expanded=True,
):

    salary = st.number_input(
        "Monthly take-home salary",
        min_value=0.0,
        value=float(settings["salary"]),
        step=1000.0,
    )

    savings = st.number_input(
        "Current savings",
        min_value=0.0,
        value=float(settings["savings"]),
        step=1000.0,
    )

    bonus = st.number_input(
        "Bonus this month",
        min_value=0.0,
        value=float(settings["bonus"]),
        step=5000.0,
    )

    annual_salary = st.number_input(
        "Annual salary",
        min_value=0.0,
        value=float(settings["annual_salary"]),
        step=10000.0,
    )

    increment = st.number_input(
        "Expected increment %",
        min_value=0.0,
        value=float(settings["increment_pct"]),
        step=1.0,
    )

    if st.button(
        "Save income",
        use_container_width=True,
    ):

        set_setting("salary", salary)
        set_setting("savings", savings)
        set_setting("bonus", bonus)
        set_setting("annual_salary", annual_salary)
        set_setting("increment_pct", increment)

        st.success("Income updated.")

        st.rerun()


# ============================================================
# LIVING EXPENSES
# ============================================================

with st.sidebar.expander(
    "🏠 Living Expenses",
    expanded=False,
):

    expense_values = {}

    expense_items = [

        ("rent", "Rent"),

        ("fuel", "Fuel"),

        ("groceries", "Groceries"),

        ("misc", "Miscellaneous"),

        ("jio", "JioFiber"),

        ("salon", "Salon"),

    ]

    for key, label in expense_items:

        expense_values[key] = st.number_input(
            label,
            min_value=0.0,
            value=float(settings[key]),
            step=100.0,
        )

    if st.button(
        "Save living expenses",
        use_container_width=True,
    ):

        for key, value in expense_values.items():

            set_setting(key, value)

        st.success("Living expenses updated.")

        st.rerun()


# ============================================================
# DEBT SETTINGS
# ============================================================

with st.sidebar.expander(
    "💳 Debt Rules",
    expanded=False,
):

    cheq_fee = st.number_input(
        "CheQ fee per rotated card",
        min_value=0.0,
        value=float(settings["cheq_fee_per_card"]),
        step=100.0,
    )

    emergency_buffer = st.number_input(
        "Minimum emergency buffer",
        min_value=0.0,
        value=float(settings["emergency_buffer"]),
        step=1000.0,
    )

    if st.button(
        "Save debt rules",
        use_container_width=True,
    ):

        set_setting(
            "cheq_fee_per_card",
            cheq_fee,
        )

        set_setting(
            "emergency_buffer",
            emergency_buffer,
        )

        st.success("Debt rules updated.")

        st.rerun()


# ============================================================
# REFRESH DATA
# ============================================================

settings = get_settings()

loans = loans_df()

cards = cards_df()

# ============================================================
# CALCULATIONS
# ============================================================

active_loans = loans[
    loans["active"] == 1
]

active_cards = cards[
    cards["active"] == 1
]


# Monthly EMI
monthly_emi = float(
    active_loans["emi"].sum()
)


# Estimated remaining EMI outflow
estimated_loan_outstanding = float(
    (
        active_loans["emi"]
        *
        active_loans["pending_months"]
    ).sum()
)


# Living expenses
living_expenses = sum(
    settings[key]
    for key in [
        "rent",
        "fuel",
        "groceries",
        "misc",
        "jio",
        "salon",
    ]
)


# Card balances
card_balance = float(
    active_cards["balance"].sum()
)


# Card minimums
card_minimums = float(
    active_cards["min_due"].sum()
)


# CheQ cost if all active cards rotated
potential_cheq_fees = (
    len(active_cards)
    *
    settings["cheq_fee_per_card"]
)


# Monthly structural gap
monthly_required = (
    monthly_emi
    +
    living_expenses
)


monthly_gap = (
    monthly_required
    -
    settings["salary"]
)


# Expected salary after increment
expected_annual_salary = (
    settings["annual_salary"]
    *
    (
        1
        +
        settings["increment_pct"]
        /
        100
    )
)

expected_monthly_gross = (
    expected_annual_salary
    /
    12
)


# ============================================================
# HEADER
# ============================================================

st.title(
    "💰 Debt Manager — Real Cash Flow & Exit Plan"
)

st.caption(
    "This is an action dashboard. "
    "Record what actually happened and the recommendations change."
)


# ============================================================
# TOP METRICS
# ============================================================

col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "Monthly EMIs",
    money(monthly_emi),
)

col2.metric(
    "Living Costs",
    money(living_expenses),
)

col3.metric(
    "Card Balance",
    money(card_balance),
)

if monthly_gap > 0:

    col4.metric(
        "Monthly Shortfall",
        money(monthly_gap),
    )

else:

    col4.metric(
        "Monthly Surplus",
        money(abs(monthly_gap)),
    )


# ============================================================
# MAIN TABS
# ============================================================

tabs = st.tabs(
    [
        "🏠 Action Plan",
        "🏦 Loans",
        "💳 Cards + CheQ",
        "💸 Expenses",
        "📈 Forecast",
        "⚙️ Data",
    ]
)


# ============================================================
# ACTION PLAN
# ============================================================

with tabs[0]:

    st.header(
        "What should you do right now?"
    )

    # --------------------------------------------------------
    # MAIN FINANCIAL DIAGNOSIS
    # --------------------------------------------------------

    if monthly_gap > 0:

        st.error(
            f"""
            Your current salary does not cover your normal monthly
            commitments.

            Salary: {money(settings["salary"])}

            Living expenses: {money(living_expenses)}

            EMIs: {money(monthly_emi)}

            Monthly shortfall: {money(monthly_gap)}

            This is the main reason you are relying on credit-card
            rotation.
            """
        )

    else:

        st.success(
            f"""
            Your salary currently covers your living expenses and EMIs.

            You have approximately
            {money(abs(monthly_gap))}
            left before extra debt payments.
            """
        )


    # --------------------------------------------------------
    # CHEQ WARNING
    # --------------------------------------------------------

    if len(active_cards) > 0:

        st.warning(
            f"""
            If you rotate all {len(active_cards)} cards through CheQ,
            the estimated convenience cost is:

            {money(potential_cheq_fees)}

            per rotation cycle.

            This should be treated as a real expense, not as debt
            repayment.
            """
        )


    # --------------------------------------------------------
    # CURRENT MONTH SIMULATION
    # --------------------------------------------------------

    st.header(
        "📅 This Month Cash Simulation"
    )

    st.caption(
        "This shows whether your current cash can survive the month."
    )


    starting_savings = settings["savings"]

    salary_received = settings["salary"]

    bonus_received = settings["bonus"]

    friend_repayment = settings["friend_loan"]


    total_cash_available = (
        starting_savings
        +
        salary_received
        +
        bonus_received
    )


    cash_after_friend = (
        total_cash_available
        -
        friend_repayment
    )


    cash_after_living = (
        cash_after_friend
        -
        living_expenses
    )


    cash_after_emi = (
        cash_after_living
        -
        monthly_emi
    )


    cash_after_cards = (
        cash_after_emi
        -
        card_minimums
    )


    simulation = pd.DataFrame(
        [
            [
                "Starting savings",
                starting_savings,
            ],
            [
                "Salary",
                salary_received,
            ],
            [
                "Bonus",
                bonus_received,
            ],
            [
                "Friend loan repayment",
                -friend_repayment,
            ],
            [
                "Living expenses",
                -living_expenses,
            ],
            [
                "Scheduled EMIs",
                -monthly_emi,
            ],
            [
                "Card minimum payments",
                -card_minimums,
            ],
            [
                "Cash remaining",
                cash_after_cards,
            ],
        ],
        columns=[
            "Item",
            "Amount",
        ],
    )


    # Format money as text so Streamlit never displays 1e+04
    simulation["Amount"] = simulation[
        "Amount"
    ].apply(money)


    st.dataframe(
        simulation,
        hide_index=True,
        use_container_width=True,
    )


    # --------------------------------------------------------
    # CASH RESULT
    # --------------------------------------------------------

    if cash_after_cards < 0:

        st.error(
            f"""
            🔴 You are approximately
            {money(abs(cash_after_cards))}
            short after clearing your friend loan,
            living expenses, EMIs and card minimums.

            Therefore:

            **Do NOT make an extra loan/card payment this month.**

            Your priority is preventing another borrowing cycle.
            """
        )

    elif cash_after_cards < settings["emergency_buffer"]:

        st.warning(
            f"""
            🟠 You would have only
            {money(cash_after_cards)}
            remaining.

            Keep this as cash buffer instead of making an aggressive
            extra debt payment.
            """
        )

    else:

        extra_available = (
            cash_after_cards
            -
            settings["emergency_buffer"]
        )

        st.success(
            f"""
            🟢 After mandatory payments you have
            {money(cash_after_cards)}
            remaining.

            After keeping your
            {money(settings["emergency_buffer"])}
            emergency buffer, approximately

            **{money(extra_available)}**

            could potentially be used for debt reduction.
            """
        )


    # ========================================================
    # RECOMMENDATIONS
    # ========================================================

    st.header(
        "🎯 Your Debt Strategy"
    )


    recommendations = []


    # Recommendation 1
    if settings["friend_loan"] > 0:

        recommendations.append(
            (
                "1️⃣",
                "Clear the friend loan",
                f"""
                You have a personal loan of
                {money(settings["friend_loan"])}
                that you said needs to be cleared this month.

                Handle this before aggressive credit-card repayment.
                """
            )
        )


    # Recommendation 2
    recommendations.append(
        (
            "2️⃣",
            "Stop increasing revolving debt",
            f"""
            Your three cards total approximately
            {money(card_balance)}.

            Paying the cards and immediately recycling the money
            through CheQ does not eliminate the underlying borrowing.

            The objective is:

            **Total card/CheQ debt ↓ every month.**
            """
        )
    )


    # Recommendation 3
    recommendations.append(
        (
            "3️⃣",
            "Let short loans finish",
            """
            Do not replace an EMI that disappears with new spending.

            Every finished loan creates permanent monthly cash flow.
            That freed amount should be redirected toward your
            revolving debt.
            """
        )
    )


    # Recommendation 4
    recommendations.append(
        (
            "4️⃣",
            "Build a controlled cash buffer",
            f"""
            Keep at least
            {money(settings["emergency_buffer"])}
            available.

            Without a buffer, even a small emergency can push you
            back into card/CheQ borrowing.
            """
        )
    )


    # Recommendation 5
    recommendations.append(
        (
            "5️⃣",
            "Use every freed EMI for debt reduction",
            """
            When an EMI disappears, treat that money as already
            committed to debt repayment.

            Do not increase your lifestyle spending.
            """
        )
    )


    for number, title, description in recommendations:

        st.markdown(
            f"""
            ### {number} {title}

            {description}
            """
        )


# ============================================================
# LOANS
# ============================================================

with tabs[1]:

    st.header(
        "🏦 Loan Management"
    )

    st.caption(
        "Record each EMI after you actually pay it."
    )


    display_loans = loans.copy()

    display_loans[
        "Estimated Remaining"
    ] = (
        display_loans["emi"]
        *
        display_loans["pending_months"]
    )


    display_loans[
        "EMI"
    ] = display_loans["emi"].apply(money)

    display_loans[
        "Estimated Remaining"
    ] = display_loans[
        "Estimated Remaining"
    ].apply(money)


    display_loans = display_loans[
        [
            "name",
            "EMI",
            "pending_months",
            "emi_day",
            "Estimated Remaining",
        ]
    ]


    display_loans.columns = [
        "Loan",
        "Monthly EMI",
        "Months Left",
        "EMI Day",
        "Remaining EMI Outflow",
    ]


    st.dataframe(
        display_loans,
        hide_index=True,
        use_container_width=True,
    )


    # --------------------------------------------------------
    # RECORD PAYMENT
    # --------------------------------------------------------

    st.subheader(
        "✅ Record a loan payment"
    )


    loan_map = dict(
        zip(
            loans["name"],
            loans["id"],
        )
    )


    with st.form("loan_payment_form"):

        loan_name = st.selectbox(
            "Loan",
            list(loan_map.keys()),
        )

        amount_paid = st.number_input(
            "Amount actually paid",
            min_value=0.0,
            step=100.0,
        )

        months_reduced = st.number_input(
            "Months reduced",
            min_value=1,
            max_value=60,
            value=1,
            step=1,
        )

        payment_note = st.text_input(
            "Note",
            "Regular EMI",
        )

        submit_payment = st.form_submit_button(
            "Record payment",
            use_container_width=True,
        )


    if submit_payment:

        conn = db()

        loan_id = loan_map[
            loan_name
        ]


        conn.execute(
            """
            INSERT INTO loan_payments
            (
                loan_id,
                pay_date,
                amount,
                months_reduced,
                note
            )
            VALUES (?,?,?,?,?)
            """,
            (
                loan_id,
                str(today),
                amount_paid,
                months_reduced,
                payment_note,
            ),
        )


        conn.execute(
            """
            UPDATE loans

            SET

                pending_months =
                    MAX(
                        0,
                        pending_months - ?
                    ),

                active =
                    CASE
                        WHEN pending_months - ? <= 0
                        THEN 0
                        ELSE 1
                    END

            WHERE id = ?
            """,
            (
                months_reduced,
                months_reduced,
                loan_id,
            ),
        )


        conn.commit()
        conn.close()


        st.success(
            f"{loan_name} updated successfully."
        )

        st.rerun()


    # --------------------------------------------------------
    # NEW LOAN
    # --------------------------------------------------------

    st.subheader(
        "➕ Add a new loan"
    )


    with st.form("new_loan_form"):

        lender = st.text_input(
            "Lender"
        )

        loan_amount = st.number_input(
            "Loan amount",
            min_value=0.0,
            step=1000.0,
        )

        new_emi = st.number_input(
            "Monthly EMI",
            min_value=0.0,
            step=100.0,
        )

        loan_months = st.number_input(
            "Number of months",
            min_value=1,
            max_value=120,
            value=6,
        )

        loan_reason = st.text_input(
            "Reason for loan"
        )

        add_loan = st.form_submit_button(
            "Add loan",
            use_container_width=True,
        )


    if add_loan:

        if lender and loan_amount > 0:

            conn = db()

            conn.execute(
                """
                INSERT INTO new_debts
                (
                    debt_date,
                    lender,
                    amount,
                    monthly_payment,
                    months,
                    note
                )
                VALUES (?,?,?,?,?,?)
                """,
                (
                    str(today),
                    lender,
                    loan_amount,
                    new_emi,
                    loan_months,
                    loan_reason,
                ),
            )


            conn.execute(
                """
                INSERT OR IGNORE INTO loans
                (
                    name,
                    emi,
                    pending_months,
                    emi_day,
                    rotatable
                )
                VALUES (?,?,?,?,?)
                """,
                (
                    lender,
                    new_emi,
                    loan_months,
                    1,
                    0,
                ),
            )


            conn.commit()
            conn.close()


            st.success(
                "New loan added."
            )

            st.rerun()


    # --------------------------------------------------------
    # PAYMENT HISTORY
    # --------------------------------------------------------

    payment_history = payments_df()


    if not payment_history.empty:

        st.subheader(
            "Recent loan payments"
        )

        st.dataframe(
            payment_history,
            hide_index=True,
            use_container_width=True,
        )


# ============================================================
# CARDS + CHEQ
# ============================================================

with tabs[2]:

    st.header(
        "💳 Credit Cards + CheQ"
    )


    st.warning(
        """
        Important:

        If you pay a credit card in full and then use CheQ to
        move the money back into your bank account, the card may
        show ₹0 but the debt has NOT actually disappeared.

        Record the recycled amount here.
        """
    )


    card_display = cards.copy()


    card_display["balance"] = (
        card_display["balance"]
        .apply(money)
    )

    card_display["min_due"] = (
        card_display["min_due"]
        .apply(money)
    )


    card_display = card_display[
        [
            "name",
            "balance",
            "min_due",
            "due_day",
        ]
    ]


    card_display.columns = [
        "Card",
        "Current Balance",
        "Minimum Due",
        "Due Day",
    ]


    st.dataframe(
        card_display,
        hide_index=True,
        use_container_width=True,
    )


    # --------------------------------------------------------
    # RECORD CARD ROTATION
    # --------------------------------------------------------

    st.subheader(
        "🔄 Record a card / CheQ rotation"
    )


    card_map = dict(
        zip(
            cards["name"],
            cards["id"],
        )
    )


    with st.form("card_cycle_form"):

        card_name = st.selectbox(
            "Card",
            list(card_map.keys()),
        )


        bill_paid = st.number_input(
            "Card bill paid",
            min_value=0.0,
            step=1000.0,
        )


        recycled_amount = st.number_input(
            "Amount received back through CheQ",
            min_value=0.0,
            step=1000.0,
        )


        convenience_fee = st.number_input(
            "CheQ convenience fee",
            min_value=0.0,
            value=float(
                settings["cheq_fee_per_card"]
            ),
            step=100.0,
        )


        new_card_spend = st.number_input(
            "New card spending after payment",
            min_value=0.0,
            step=500.0,
        )


        card_note = st.text_input(
            "Note"
        )


        record_cycle = st.form_submit_button(
            "Record card cycle",
            use_container_width=True,
        )


    if record_cycle:

        conn = db()

        card_id = card_map[
            card_name
        ]


        conn.execute(
            """
            INSERT INTO card_cycles
            (
                card_id,
                cycle_date,
                paid_amount,
                recycled_amount,
                cheq_fee,
                note
            )
            VALUES (?,?,?,?,?,?)
            """,
            (
                card_id,
                str(today),
                bill_paid,
                recycled_amount,
                convenience_fee,
                card_note,
            ),
        )


        # Approximate card balance update
        conn.execute(
            """
            UPDATE cards

            SET balance =
                MAX(
                    0,
                    balance
                    - ?
                    + ?
                )

            WHERE id = ?
            """,
            (
                bill_paid,
                new_card_spend,
                card_id,
            ),
        )


        conn.commit()
        conn.close()


        st.success(
            "Card cycle recorded."
        )

        st.rerun()


    # --------------------------------------------------------
    # CHEQ INSIGHT
    # --------------------------------------------------------

    cycles = card_cycles_df()


    if not cycles.empty:

        total_recycled = (
            cycles[
                "recycled_amount"
            ].sum()
        )

        total_cheq_fees = (
            cycles[
                "cheq_fee"
            ].sum()
        )


        col1, col2 = st.columns(2)


        col1.metric(
            "Recorded CheQ Recycling",
            money(total_recycled),
        )


        col2.metric(
            "Recorded CheQ Fees",
            money(total_cheq_fees),
        )


        st.subheader(
            "Card/CheQ history"
        )


        display_cycles = cycles.copy()


        for col in [
            "paid_amount",
            "recycled_amount",
            "cheq_fee",
        ]:

            display_cycles[col] = (
                display_cycles[col]
                .apply(money)
            )


        st.dataframe(
            display_cycles,
            hide_index=True,
            use_container_width=True,
        )


# ============================================================
# EXPENSES
# ============================================================

with tabs[3]:

    st.header(
        "💸 Real-Time Expense Management"
    )


    st.caption(
        "Enter expenses as they happen. "
        "The app will show where your money is actually going."
    )


    categories = [

        "Rent",

        "Fuel",

        "Groceries",

        "Miscellaneous",

        "JioFiber",

        "Salon",

        "Food",

        "Shopping",

        "Travel",

        "Medical",

        "Entertainment",

        "Other",

    ]


    with st.form("expense_form"):

        expense_date = st.date_input(
            "Date",
            today,
        )


        category = st.selectbox(
            "Category",
            categories,
        )


        expense_amount = st.number_input(
            "Amount",
            min_value=0.0,
            step=100.0,
        )


        description = st.text_input(
            "Description"
        )


        add_expense = st.form_submit_button(
            "Add expense",
            use_container_width=True,
        )


    if add_expense:

        if expense_amount > 0:

            conn = db()


            conn.execute(
                """
                INSERT INTO transactions
                (
                    txn_date,
                    category,
                    amount,
                    kind,
                    note
                )
                VALUES (?,?,?,?,?)
                """,
                (
                    str(expense_date),
                    category,
                    expense_amount,
                    "expense",
                    description,
                ),
            )


            conn.commit()
            conn.close()


            st.success(
                "Expense added."
            )


            st.rerun()


    expenses = expenses_df()


    if not expenses.empty:

        expenses[
            "txn_date"
        ] = pd.to_datetime(
            expenses["txn_date"]
        )


        current_month = expenses[
            (
                expenses["txn_date"].dt.year
                == today.year
            )
            &
            (
                expenses["txn_date"].dt.month
                == today.month
            )
        ]


        if not current_month.empty:

            st.subheader(
                "📊 Spending this month"
            )


            category_totals = (
                current_month
                .groupby("category")[
                    "amount"
                ]
                .sum()
                .sort_values(
                    ascending=False
                )
                .reset_index()
            )


            category_totals["amount"] = (
                category_totals["amount"]
                .apply(money)
            )


            st.dataframe(
                category_totals,
                hide_index=True,
                use_container_width=True,
            )


            # Numeric chart data
            chart_data = (
                current_month
                .groupby("category")[
                    "amount"
                ]
                .sum()
            )


            st.bar_chart(
                chart_data
            )


        st.subheader(
            "Recent expenses"
        )


        recent_expenses = expenses.head(30).copy()


        recent_expenses["amount"] = (
            recent_expenses["amount"]
            .apply(money)
        )


        st.dataframe(
            recent_expenses,
            hide_index=True,
            use_container_width=True,
        )


# ============================================================
# FORECAST
# ============================================================

with tabs[4]:

    st.header(
        "📈 Debt Escape Forecast"
    )


    st.caption(
        "This is a planning model using the EMI durations you entered. "
        "Actual lender balances can differ."
    )


    if not active_loans.empty:

        max_months = max(
            36,
            int(
                active_loans[
                    "pending_months"
                ].max()
            )
            + 3,
        )


        forecast_rows = []


        for month in range(
            1,
            max_months + 1,
        ):

            emi_remaining = float(
                active_loans.loc[
                    active_loans[
                        "pending_months"
                    ]
                    >= month,
                    "emi",
                ].sum()
            )


            emi_freed = (
                monthly_emi
                -
                emi_remaining
            )


            cash_flow_gap = (
                emi_remaining
                +
                living_expenses
                -
                settings["salary"]
            )


            forecast_rows.append(
                [
                    month,
                    emi_remaining,
                    emi_freed,
                    cash_flow_gap,
                ]
            )


        forecast = pd.DataFrame(
            forecast_rows,
            columns=[
                "Month",
                "Scheduled EMIs",
                "EMI Freed",
                "Cash Flow Gap",
            ],
        )


        # ----------------------------------------------------
        # CHART
        # ----------------------------------------------------

        chart = forecast.set_index(
            "Month"
        )[
            [
                "Scheduled EMIs",
                "EMI Freed",
            ]
        ]


        st.line_chart(
            chart
        )


        # ----------------------------------------------------
        # TABLE
        # ----------------------------------------------------

        display_forecast = forecast.head(
            24
        ).copy()


        for col in [
            "Scheduled EMIs",
            "EMI Freed",
            "Cash Flow Gap",
        ]:

            display_forecast[col] = (
                display_forecast[col]
                .apply(money)
            )


        st.dataframe(
            display_forecast,
            hide_index=True,
            use_container_width=True,
        )


    # --------------------------------------------------------
    # LOAN MILESTONES
    # --------------------------------------------------------

    st.subheader(
        "🎯 Loans that finish first"
    )


    milestones = active_loans.sort_values(
        "pending_months"
    )[
        [
            "name",
            "emi",
            "pending_months",
        ]
    ].copy()


    milestones[
        "EMI Freed"
    ] = milestones["emi"].apply(
        money
    )


    milestones[
        "emi"
    ] = milestones[
        "emi"
    ].apply(
        money
    )


    milestones.columns = [
        "Loan",
        "Monthly EMI",
        "Months Left",
        "Monthly Cash Freed",
    ]


    st.dataframe(
        milestones,
        hide_index=True,
        use_container_width=True,
    )


    st.success(
        """
        The key strategy is simple:

        **Loan finishes → EMI disappears → immediately redirect
        that EMI toward your revolving debt.**

        Do not allow the freed EMI to become lifestyle spending.
        """
    )


# ============================================================
# DATA
# ============================================================

with tabs[5]:

    st.header(
        "⚙️ Data"
    )


    st.info(
        """
        Your data is stored locally in:

        `debt_manager.db`

        Keep this file if you want to preserve your history.
        """
    )


    # --------------------------------------------------------
    # DOWNLOAD DATA
    # --------------------------------------------------------

    st.subheader(
        "Download your data"
    )


    st.download_button(
        "Download Loans CSV",
        loans.to_csv(
            index=False
        ).encode("utf-8"),
        "loans.csv",
        "text/csv",
    )


    st.download_button(
        "Download Cards CSV",
        cards.to_csv(
            index=False
        ).encode("utf-8"),
        "cards.csv",
        "text/csv",
    )


    st.download_button(
        "Download Expenses CSV",
        expenses_df()
        .to_csv(
            index=False
        )
        .encode("utf-8"),
        "expenses.csv",
        "text/csv",
    )


    # --------------------------------------------------------
    # RESET
    # --------------------------------------------------------

    st.divider()


    st.subheader(
        "⚠️ Reset"
    )


    st.warning(
        "Resetting deletes your locally stored transactions and restores the original starting data."
    )


    if st.button(
        "Reset database",
        type="secondary",
    ):

        if DB_PATH.exists():

            DB_PATH.unlink()


        st.success(
            "Database reset."
        )


        st.rerun()


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    """
    Debt Manager is a budgeting and decision-support tool.
    Always verify lender balances, interest, fees, due dates and
    CheQ charges before making financial decisions.
    """
)
