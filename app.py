import streamlit as st
import sqlite3
from pathlib import Path
from datetime import date
import pandas as pd
import calendar

# ============================================================
# CONFIG
# ============================================================

st.set_page_config(
    page_title="Debt Escape Planner",
    page_icon="💰",
    layout="wide"
)

APP_DIR = Path(__file__).parent
DB_PATH = APP_DIR / "debt_manager.db"

TODAY = date.today()


# ============================================================
# MONEY FORMAT
# ============================================================

def money(x):
    try:
        x = float(x or 0)
    except:
        x = 0

    sign = "-" if x < 0 else ""

    return f"{sign}₹{abs(x):,.0f}"


# ============================================================
# DATABASE
# ============================================================

def get_db():

    conn = sqlite3.connect(
        DB_PATH,
        check_same_thread=False
    )

    conn.row_factory = sqlite3.Row

    return conn


def init_db():

    conn = get_db()

    c = conn.cursor()

    # --------------------------------------------------------
    # SETTINGS
    # --------------------------------------------------------

    c.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value REAL
        )
    """)

    # --------------------------------------------------------
    # LOANS
    # --------------------------------------------------------

    c.execute("""
        CREATE TABLE IF NOT EXISTS loans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            emi REAL,
            pending_months INTEGER,
            emi_day INTEGER,
            active INTEGER DEFAULT 1,
            foreclosure_amount REAL DEFAULT 0
        )
    """)

    # --------------------------------------------------------
    # CARDS
    # --------------------------------------------------------

    c.execute("""
        CREATE TABLE IF NOT EXISTS cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            balance REAL,
            min_due REAL,
            active INTEGER DEFAULT 1
        )
    """)

    # --------------------------------------------------------
    # EXPENSES
    # --------------------------------------------------------

    c.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            expense_date TEXT,
            category TEXT,
            amount REAL,
            note TEXT
        )
    """)

    # --------------------------------------------------------
    # LOAN PAYMENTS
    # --------------------------------------------------------

    c.execute("""
        CREATE TABLE IF NOT EXISTS loan_payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            loan_id INTEGER,
            payment_date TEXT,
            amount REAL,
            months_reduced INTEGER,
            note TEXT
        )
    """)

    # --------------------------------------------------------
    # CARD ROTATIONS
    # --------------------------------------------------------

    c.execute("""
        CREATE TABLE IF NOT EXISTS card_rotations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            card_id INTEGER,
            rotation_date TEXT,
            bill_paid REAL,
            recycled REAL,
            fee REAL,
            note TEXT
        )
    """)

    # ========================================================
    # DEFAULT SETTINGS
    # ========================================================

    defaults = {

        "salary": 59000,

        "annual_salary": 723256,

        "increment": 10,

        "bonus": 60000,

        "cash": 40000,

        "friend_loan": 80000,

        "rent": 15000,

        "fuel": 2000,

        "groceries": 2000,

        "misc": 2000,

        "jio": 1200,

        "salon": 2000,

        "cheq_fee": 2000,

        "minimum_buffer": 10000,

        # Planning begins after September
        "planning_year": 2026,

        "planning_month": 9,

        "planning_day": 26
    }

    for key, value in defaults.items():

        c.execute(
            """
            INSERT OR IGNORE INTO settings
            (key,value)
            VALUES (?,?)
            """,
            (key,value)
        )

    # ========================================================
    # LOANS
    #
    # IMPORTANT:
    # September EMI is already completed.
    # Therefore these are MONTHS LEFT AFTER SEPTEMBER.
    # ========================================================

    loans = [

        ("Fibe", 9890, 6, 4),

        ("Stashfin", 4199, 11, 2),

        ("Kredibee", 9219, 5, 2),

        ("Branch", 2488, 4, 28),

        ("Money View", 3764, 5, 3),

        ("Poonawala Fincorp", 6507, 21, 5),

        ("Instamoney", 5616, 2, 1),

        ("Kissht", 1583, 8, 7),

        ("Loan Tap", 5276, 1, 1),

        ("Flexipay", 6000, 23, 26)
    ]

    for loan in loans:

        c.execute(
            """
            INSERT OR IGNORE INTO loans
            (name,emi,pending_months,emi_day)
            VALUES (?,?,?,?)
            """,
            loan
        )

    # ========================================================
    # CARDS
    # ========================================================

    cards = [

        ("Axis", 60000, 2000),

        ("HDFC", 29656, 1816),

        ("DBS", 36000, 1089.79)
    ]

    for card in cards:

        c.execute(
            """
            INSERT OR IGNORE INTO cards
            (name,balance,min_due)
            VALUES (?,?,?)
            """,
            card
        )

    conn.commit()

    conn.close()


init_db()


# ============================================================
# DATA FUNCTIONS
# ============================================================

def settings():

    conn = get_db()

    rows = conn.execute(
        "SELECT key,value FROM settings"
    ).fetchall()

    conn.close()

    return {
        r["key"]: r["value"]
        for r in rows
    }


def save_setting(key,value):

    conn = get_db()

    conn.execute(
        """
        INSERT OR REPLACE INTO settings
        (key,value)
        VALUES (?,?)
        """,
        (key,value)
    )

    conn.commit()

    conn.close()


def get_loans():

    conn = get_db()

    df = pd.read_sql_query(
        """
        SELECT *
        FROM loans
        ORDER BY pending_months
        """,
        conn
    )

    conn.close()

    return df


def get_cards():

    conn = get_db()

    df = pd.read_sql_query(
        """
        SELECT *
        FROM cards
        WHERE active=1
        """,
        conn
    )

    conn.close()

    return df


def get_expenses():

    conn = get_db()

    df = pd.read_sql_query(
        """
        SELECT *
        FROM expenses
        ORDER BY expense_date DESC,id DESC
        """,
        conn
    )

    conn.close()

    return df


def get_rotations():

    conn = get_db()

    df = pd.read_sql_query(
        """
        SELECT
            cr.*,
            c.name
        FROM card_rotations cr
        LEFT JOIN cards c
        ON cr.card_id=c.id
        ORDER BY rotation_date DESC
        """,
        conn
    )

    conn.close()

    return df


# ============================================================
# CURRENT DATA
# ============================================================

S = settings()

loans = get_loans()

cards = get_cards()

active_loans = loans[
    loans["active"] == 1
].copy()


# ============================================================
# LIVING COST
# ============================================================

living_cost = sum(
    S[x]
    for x in [
        "rent",
        "fuel",
        "groceries",
        "misc",
        "jio",
        "salon"
    ]
)


# ============================================================
# CARD DATA
# ============================================================

card_total = float(
    cards["balance"].sum()
)

card_minimum = float(
    cards["min_due"].sum()
)


# ============================================================
# CURRENT EMI
# ============================================================

current_emi = float(
    active_loans["emi"].sum()
)


# ============================================================
# APP HEADER
# ============================================================

st.title(
    "💰 Debt Escape Planner"
)

st.caption(
    "Planning starts from 26 September 2026 because September EMIs are already paid."
)


# ============================================================
# TOP STATUS
# ============================================================

c1,c2,c3,c4,c5 = st.columns(5)

c1.metric(
    "Cash now",
    money(S["cash"])
)

c2.metric(
    "Bonus",
    money(S["bonus"])
)

c3.metric(
    "Friend repayment",
    money(S["friend_loan"])
)

c4.metric(
    "Oct EMI",
    money(current_emi)
)

c5.metric(
    "Card balances",
    money(card_total)
)


# ============================================================
# NAVIGATION
# ============================================================

tabs = st.tabs(
    [
        "🚨 COMMAND CENTER",
        "💡 USE MY ₹40K / ₹60K",
        "📅 EMI FORECAST",
        "🏦 LOANS",
        "💳 CARDS + CHEQ",
        "💸 EXPENSES",
        "⚙️ SETTINGS"
    ]
)


# ============================================================
# COMMAND CENTER
# ============================================================

with tabs[0]:

    st.header(
        "🚨 Your Financial Command Center"
    )


    # --------------------------------------------------------
    # CASH AFTER FRIEND
    # --------------------------------------------------------

    cash_after_friend = (
        S["cash"]
        +
        S["bonus"]
        -
        S["friend_loan"]
    )


    st.subheader(
        "1. Your starting position — 26 September"
    )


    start = pd.DataFrame(
        [
            [
                "Current cash",
                S["cash"]
            ],

            [
                "September salary/bonus",
                S["bonus"]
            ],

            [
                "Friend repayment",
                -S["friend_loan"]
            ],

            [
                "Strategic cash remaining",
                cash_after_friend
            ]
        ],
        columns=[
            "Item",
            "Amount"
        ]
    )


    start["Amount"] = (
        start["Amount"]
        .apply(money)
    )


    st.dataframe(
        start,
        hide_index=True,
        use_container_width=True
    )


    # --------------------------------------------------------
    # MONTHLY FORECAST
    # --------------------------------------------------------

    rows = []

    cumulative_deficit = 0

    positive_month = None


    for month in range(1,25):

        emi = float(
            active_loans.loc[
                active_loans[
                    "pending_months"
                ] >= month,
                "emi"
            ].sum()
        )


        cash_flow = (
            S["salary"]
            -
            living_cost
            -
            emi
        )


        deficit = max(
            0,
            -cash_flow
        )


        cumulative_deficit += deficit


        if (
            positive_month is None
            and
            cash_flow >= 0
        ):

            positive_month = month


        rows.append(
            {
                "Month": month,
                "EMI": emi,
                "Salary": S["salary"],
                "Living": living_cost,
                "Cash Flow": cash_flow,
                "Deficit": deficit,
                "Cumulative Deficit":
                    cumulative_deficit
            }
        )


    forecast = pd.DataFrame(rows)


    # --------------------------------------------------------
    # BRIDGE
    # --------------------------------------------------------

    if positive_month:

        bridge_months = (
            positive_month - 1
        )

        bridge_needed = float(
            forecast[
                forecast["Month"]
                <= bridge_months
            ]["Deficit"].sum()
        )

    else:

        bridge_months = 24

        bridge_needed = float(
            forecast["Deficit"].sum()
        )


    st.subheader(
        "2. 🚨 Your NO-NEW-LOAN bridge"
    )


    if positive_month:

        st.success(
            f"""
            Your salary becomes sufficient to cover living costs
            + EMIs in **Month {positive_month}**.

            Until then, you need to bridge approximately:

            ## {money(bridge_needed)}

            The important thing is that this shortage is
            **temporary**, provided you don't add another EMI.
            """
        )


    # --------------------------------------------------------
    # STRATEGY
    # --------------------------------------------------------

    st.subheader(
        "3. 🎯 What I recommend"
    )


    if cash_after_friend > 0:

        st.info(
            f"""
            You have approximately **{money(cash_after_friend)}**
            left after paying your friend.

            **Do NOT immediately put all of this into a card.**

            First evaluate whether closing an EMI can reduce your
            monthly cash-flow pressure.

            The app's next screen compares your options.
            """
        )


    # --------------------------------------------------------
    # OCTOBER
    # --------------------------------------------------------

    october = forecast.iloc[0]

    st.subheader(
        "4. 📅 October 2026"
    )


    if october["Cash Flow"] < 0:

        st.error(
            f"""
            October cash flow:

            Salary: {money(october["Salary"])}

            Living: {money(october["Living"])}

            EMIs: {money(october["EMI"])}

            **Shortage: {money(october["Deficit"])}**
            """
        )


    # --------------------------------------------------------
    # UPCOMING EMI
    # --------------------------------------------------------

    st.subheader(
        "5. 🚀 First EMIs that disappear"
    )


    upcoming = active_loans.sort_values(
        "pending_months"
    ).head(5).copy()


    for _,row in upcoming.iterrows():

        st.markdown(
            f"""
            ### {row["name"]}

            **{int(row["pending_months"])} month(s) remaining**

            Monthly burden:
            **{money(row["emi"])}**

            When this finishes:
            **{money(row["emi"])} / month is permanently freed.**
            """
        )


# ============================================================
# USE MY MONEY
# ============================================================

with tabs[1]:

    st.header(
        "💡 What should I do with my ₹20,000?"
    )

    st.caption(
        "This screen compares closing an EMI versus paying the cards."
    )


    strategic_cash = (
        S["cash"]
        +
        S["bonus"]
        -
        S["friend_loan"]
    )


    st.metric(
        "Cash available after friend repayment",
        money(strategic_cash)
    )


    st.divider()


    # --------------------------------------------------------
    # FORECLOSURE INPUT
    # --------------------------------------------------------

    st.subheader(
        "🏦 Step 1 — Enter actual foreclosure amounts"
    )


    st.warning(
        """
        Do NOT assume EMI × months is the foreclosure amount.

        Ask each lender:

        "What is my exact foreclosure amount today?"

        Enter it below.

        The app will then determine which closure gives you
        the best monthly relief for the cash you spend.
        """
    )


    closure_data = []


    for idx,row in active_loans.iterrows():

        estimated = (
            row["emi"]
            *
            row["pending_months"]
        )


        foreclosure = st.number_input(
            f'{row["name"]} — foreclosure amount',
            min_value=0.0,
            value=float(
                row["foreclosure_amount"]
                if row["foreclosure_amount"] > 0
                else estimated
            ),
            step=500.0,
            key=f"foreclose_{row['id']}"
        )


        if foreclosure > 0:

            monthly_relief = row["emi"]


            efficiency = (
                monthly_relief
                /
                foreclosure
            )


            closure_data.append(
                {
                    "Loan":
                        row["name"],

                    "Foreclosure":
                        foreclosure,

                    "Monthly EMI Freed":
                        monthly_relief,

                    "Months Left":
                        row["pending_months"],

                    "Efficiency":
                        efficiency
                }
            )


    closure_df = pd.DataFrame(
        closure_data
    )


    if not closure_df.empty:

        closure_df = closure_df.sort_values(
            "Efficiency",
            ascending=False
        )


        display = closure_df.copy()


        display[
            "Foreclosure"
        ] = display[
            "Foreclosure"
        ].apply(money)


        display[
            "Monthly EMI Freed"
        ] = display[
            "Monthly EMI Freed"
        ].apply(money)


        display[
            "Efficiency"
        ] = display[
            "Efficiency"
        ].apply(
            lambda x:
            f"{x:.2f}"
        )


        st.dataframe(
            display,
            hide_index=True,
            use_container_width=True
        )


        best = closure_df.iloc[0]


        st.success(
            f"""
            🏆 **Best cash-flow efficiency: {best["Loan"]}**

            Foreclosure amount:
            **{money(best["Foreclosure"])}**

            Monthly EMI eliminated:
            **{money(best["Monthly EMI Freed"])}**

            This is the strongest option based on
            **monthly cash-flow relief per rupee used**.

            However, only proceed if paying it off still leaves
            enough cash to survive the upcoming deficit period.
            """
        )


    # --------------------------------------------------------
    # CASH SAFETY TEST
    # --------------------------------------------------------

    st.subheader(
        "🛡️ Cash safety test"
    )


    amount_to_use = st.number_input(
        "How much cash are you considering using?",
        min_value=0.0,
        max_value=max(
            strategic_cash,
            0
        ),
        value=0.0,
        step=1000.0
    )


    cash_left = (
        strategic_cash
        -
        amount_to_use
    )


    if amount_to_use > 0:

        if cash_left < S["minimum_buffer"]:

            st.error(
                f"""
                🔴 **Too aggressive.**

                You would have only
                **{money(cash_left)}**
                left.

                Your minimum buffer is
                **{money(S["minimum_buffer"])}**.

                Don't use this much cash.
                """
            )

        else:

            st.success(
                f"""
                🟢 This leaves you with
                **{money(cash_left)}**
                cash.

                This is above your minimum buffer.
                """
            )


    # --------------------------------------------------------
    # CARD VS EMI
    # --------------------------------------------------------

    st.subheader(
        "💳 Should the money go toward a card instead?"
    )


    card_fee = S[
        "cheq_fee"
    ]


    st.markdown(
        f"""
        Your current card balances are approximately:

        **{money(card_total)}**

        Your estimated CheQ cost is:

        **{money(card_fee)} per card rotation**

        If you rotate all three cards:

        **{money(card_fee * 3)} per cycle**
        """
    )


    st.warning(
        """
        During a negative-cash-flow period, a large card payment
        can be counterproductive.

        If paying the card forces you to use CheQ again,
        you have not actually improved your financial position.
        """
    )


    st.markdown(
        """
        ### Decision rule

        **If cash flow is negative:**

        Preserve cash → reduce spending → minimize rotation.

        **If cash flow becomes positive:**

        Stop rotation → attack the revolving card balance.

        **If an EMI can be closed cheaply:**

        Consider foreclosure if the monthly EMI relief materially
        reduces the upcoming bridge requirement.
        """
    )


# ============================================================
# EMI FORECAST
# ============================================================

with tabs[2]:

    st.header(
        "📅 EMI Forecast from 26 September 2026"
    )


    st.caption(
        "September is treated as completely paid."
    )


    rows = []


    for month_number in range(
        1,
        25
    ):

        emi = float(
            active_loans.loc[
                active_loans[
                    "pending_months"
                ] >= month_number,
                "emi"
            ].sum()
        )


        cash_flow = (
            S["salary"]
            -
            living_cost
            -
            emi
        )


        rows.append(
            {
                "Month #":
                    month_number,

                "EMI":
                    emi,

                "Living":
                    living_cost,

                "Salary":
                    S["salary"],

                "Cash Flow":
                    cash_flow
            }
        )


    df = pd.DataFrame(
        rows
    )


    # --------------------------------------------------------
    # CALENDAR LABEL
    # --------------------------------------------------------

    labels = []


    year = 2026

    month = 10


    for i in range(
        len(df)
    ):

        labels.append(
            f"{calendar.month_abbr[month]} {year}"
        )

        month += 1

        if month == 13:

            month = 1

            year += 1


    df.insert(
        0,
        "Period",
        labels
    )


    # --------------------------------------------------------
    # POSITIVE MONTH
    # --------------------------------------------------------

    positive = df[
        df["Cash Flow"] >= 0
    ]


    if not positive.empty:

        first_positive = positive.iloc[0]


        st.success(
            f"""
            🎯 Your first positive month is:

            ## {first_positive["Period"]}

            Expected surplus:
            **{money(first_positive["Cash Flow"])}**

            This is why taking another long-term loan now would
            be dangerous — it could push this turning point further
            away.
            """
        )


    # --------------------------------------------------------
    # CHART
    # --------------------------------------------------------

    chart = df.set_index(
        "Period"
    )[[
        "EMI",
        "Cash Flow"
    ]]


    st.line_chart(
        chart
    )


    # --------------------------------------------------------
    # TABLE
    # --------------------------------------------------------

    display = df.copy()


    for col in [
        "EMI",
        "Living",
        "Salary",
        "Cash Flow"
    ]:

        display[col] = (
            display[col]
            .apply(money)
        )


    st.dataframe(
        display,
        hide_index=True,
        use_container_width=True
    )


    # --------------------------------------------------------
    # EMI CLOSURES
    # --------------------------------------------------------

    st.subheader(
        "🎯 When each EMI disappears"
    )


    for _,row in active_loans.sort_values(
        "pending_months"
    ).iterrows():

        month_num = int(
            row["pending_months"]
        )

        if month_num <= len(labels):

            finish = labels[
                month_num - 1
            ]

        else:

            finish = "After forecast"


        st.write(
            f"**{row['name']}** — "
            f"{money(row['emi'])}/month — "
            f"finishes around **{finish}**"
        )


# ============================================================
# LOANS
# ============================================================

with tabs[3]:

    st.header(
        "🏦 Loan Management"
    )


    display = active_loans.copy()


    display[
        "EMI"
    ] = display[
        "emi"
    ].apply(money)


    display[
        "Estimated Remaining"
    ] = (
        active_loans[
            "emi"
        ]
        *
        active_loans[
            "pending_months"
        ]
    ).apply(money)


    display = display[
        [
            "name",
            "EMI",
            "pending_months",
            "emi_day",
            "Estimated Remaining"
        ]
    ]


    display.columns = [
        "Loan",
        "Monthly EMI",
        "Months Left",
        "EMI Date",
        "Estimated Remaining"
    ]


    st.dataframe(
        display,
        hide_index=True,
        use_container_width=True
    )


    # --------------------------------------------------------
    # RECORD EMI
    # --------------------------------------------------------

    st.subheader(
        "✅ Record an EMI paid"
    )


    loan_map = dict(
        zip(
            active_loans["name"],
            active_loans["id"]
        )
    )


    if loan_map:

        with st.form(
            "payment_form"
        ):

            loan_name = st.selectbox(
                "Loan",
                list(
                    loan_map.keys()
                )
            )


            amount = st.number_input(
                "Amount paid",
                min_value=0.0,
                step=100.0
            )


            months_reduced = st.number_input(
                "Months reduced",
                min_value=1,
                max_value=60,
                value=1
            )


            submit = st.form_submit_button(
                "Record EMI"
            )


        if submit:

            loan_id = loan_map[
                loan_name
            ]


            conn = get_db()


            conn.execute(
                """
                INSERT INTO loan_payments
                (
                    loan_id,
                    payment_date,
                    amount,
                    months_reduced,
                    note
                )
                VALUES (?,?,?,?,?)
                """,
                (
                    loan_id,
                    str(TODAY),
                    amount,
                    months_reduced,
                    "EMI paid"
                )
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

                WHERE id=?
                """,
                (
                    months_reduced,
                    months_reduced,
                    loan_id
                )
            )


            conn.commit()

            conn.close()


            st.success(
                f"{loan_name} updated."
            )


            st.rerun()


# ============================================================
# CARDS
# ============================================================

with tabs[4]:

    st.header(
        "💳 Cards + CheQ"
    )


    st.metric(
        "Total card balance",
        money(card_total)
    )


    st.warning(
        """
        Your card strategy should change depending on your cash
        flow.

        During the negative months:

        **Avoid unnecessary card rotation.**

        Once your monthly cash flow becomes positive:

        **Stop rotation and aggressively reduce revolving debt.**
        """
    )


    card_display = cards.copy()


    card_display[
        "balance"
    ] = card_display[
        "balance"
    ].apply(money)


    card_display[
        "min_due"
    ] = card_display[
        "min_due"
    ].apply(money)


    card_display = card_display[
        [
            "name",
            "balance",
            "min_due"
        ]
    ]


    card_display.columns = [
        "Card",
        "Balance",
        "Minimum Due"
    ]


    st.dataframe(
        card_display,
        hide_index=True,
        use_container_width=True
    )


    # --------------------------------------------------------
    # CARD PRIORITY
    # --------------------------------------------------------

    st.subheader(
        "🎯 Card priority"
    )


    st.markdown(
        """
        Until your monthly cash flow becomes positive:

        **Priority 1:** keep every EMI current.

        **Priority 2:** keep required card payments current.

        **Priority 3:** minimize CheQ rotation.

        **Priority 4:** preserve cash.

        After cash flow turns positive:

        **Priority 1:** stop new card rotation.

        **Priority 2:** attack revolving card debt.

        **Priority 3:** use freed EMIs as extra card payments.
        """
    )


# ============================================================
# EXPENSES
# ============================================================

with tabs[5]:

    st.header(
        "💸 Real Spending"
    )


    categories = [
        "Food",
        "Fuel",
        "Groceries",
        "Shopping",
        "Salon",
        "Entertainment",
        "Travel",
        "Medical",
        "Miscellaneous",
        "Other"
    ]


    with st.form(
        "expense_form"
    ):

        expense_date = st.date_input(
            "Date",
            TODAY
        )


        category = st.selectbox(
            "Category",
            categories
        )


        amount = st.number_input(
            "Amount",
            min_value=0.0,
            step=100.0
        )


        note = st.text_input(
            "Description"
        )


        add = st.form_submit_button(
            "Add expense"
        )


    if add and amount > 0:

        conn = get_db()


        conn.execute(
            """
            INSERT INTO expenses
            (
                expense_date,
                category,
                amount,
                note
            )
            VALUES (?,?,?,?)
            """,
            (
                str(expense_date),
                category,
                amount,
                note
            )
        )


        conn.commit()

        conn.close()


        st.success(
            "Expense recorded."
        )


        st.rerun()


    expenses = get_expenses()


    if not expenses.empty:

        expenses[
            "expense_date"
        ] = pd.to_datetime(
            expenses[
                "expense_date"
            ]
        )


        month_expenses = expenses[
            (
                expenses[
                    "expense_date"
                ].dt.month
                ==
                TODAY.month
            )
            &
            (
                expenses[
                    "expense_date"
                ].dt.year
                ==
                TODAY.year
            )
        ]


        if not month_expenses.empty:

            totals = (
                month_expenses
                .groupby(
                    "category"
                )[
                    "amount"
                ]
                .sum()
                .sort_values(
                    ascending=False
                )
            )


            st.subheader(
                "This month's actual spending"
            )


            display = totals.reset_index()


            display[
                "amount"
            ] = display[
                "amount"
            ].apply(money)


            st.dataframe(
                display,
                hide_index=True,
                use_container_width=True
            )


            st.bar_chart(
                totals
            )


# ============================================================
# SETTINGS
# ============================================================

with tabs[6]:

    st.header(
        "⚙️ Settings"
    )


    st.subheader(
        "Income"
    )


    salary = st.number_input(
        "Monthly salary",
        value=float(S["salary"]),
        step=1000.0
    )


    bonus = st.number_input(
        "Bonus",
        value=float(S["bonus"]),
        step=5000.0
    )


    cash = st.number_input(
        "Current cash",
        value=float(S["cash"]),
        step=1000.0
    )


    friend = st.number_input(
        "Friend loan to repay",
        value=float(S["friend_loan"]),
        step=1000.0
    )


    annual = st.number_input(
        "Annual salary",
        value=float(S["annual_salary"]),
        step=10000.0
    )


    increment = st.number_input(
        "Expected increment %",
        value=float(S["increment"]),
        step=1.0
    )


    st.subheader(
        "Living costs"
    )


    rent = st.number_input(
        "Rent",
        value=float(S["rent"]),
        step=100.0
    )


    fuel = st.number_input(
        "Fuel",
        value=float(S["fuel"]),
        step=100.0
    )


    groceries = st.number_input(
        "Groceries",
        value=float(S["groceries"]),
        step=100.0
    )


    misc = st.number_input(
        "Miscellaneous",
        value=float(S["misc"]),
        step=100.0
    )


    jio = st.number_input(
        "JioFiber",
        value=float(S["jio"]),
        step=100.0
    )


    salon = st.number_input(
        "Salon",
        value=float(S["salon"]),
        step=100.0
    )


    st.subheader(
        "Debt rules"
    )


    cheq = st.number_input(
        "CheQ fee per card",
        value=float(S["cheq_fee"]),
        step=100.0
    )


    buffer = st.number_input(
        "Minimum cash buffer",
        value=float(S["minimum_buffer"]),
        step=1000.0
    )


    if st.button(
        "💾 Save settings",
        use_container_width=True
    ):

        values = {

            "salary": salary,

            "bonus": bonus,

            "cash": cash,

            "friend_loan": friend,

            "annual_salary": annual,

            "increment": increment,

            "rent": rent,

            "fuel": fuel,

            "groceries": groceries,

            "misc": misc,

            "jio": jio,

            "salon": salon,

            "cheq_fee": cheq,

            "minimum_buffer": buffer
        }


        for key,value in values.items():

            save_setting(
                key,
                value
            )


        st.success(
            "Settings saved."
        )


        st.rerun()


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    """
    Debt Escape Planner — planning tool only.
    Actual foreclosure amounts, interest, card charges and
    lender balances should always be verified with the lender.
    """
)
    sign = "-" if value < 0 else ""

    value = abs(value)

    return f"{sign}₹{value:,.0f}"


# ============================================================
# DATABASE
# ============================================================

def db():

    conn = sqlite3.connect(
        DB_PATH,
        check_same_thread=False
    )

    conn.row_factory = sqlite3.Row

    return conn


def init_db():

    conn = db()

    c = conn.cursor()

    # --------------------------------------------------------
    # SETTINGS
    # --------------------------------------------------------

    c.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value REAL
        )
    """)

    # --------------------------------------------------------
    # LOANS
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # CREDIT CARDS
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # EXPENSES
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # LOAN PAYMENTS
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # CARD / CHEQ
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # NEW DEBTS
    # --------------------------------------------------------

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
    # DEFAULT USER DATA
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

        "emergency_buffer": 10000
    }

    for key, value in defaults.items():

        c.execute(
            """
            INSERT OR IGNORE INTO settings
            (key, value)
            VALUES (?, ?)
            """,
            (key, value)
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
            (name, emi, pending_months, emi_day, rotatable)
            VALUES (?, ?, ?, ?, ?)
            """,
            loan
        )

    # ========================================================
    # CARDS
    # ========================================================

    cards = [

        # Axis minimum is an estimate
        ("Axis", 60000, 2000, 0),

        # HDFC statement supplied
        ("HDFC", 29656, 1816, 28),

        # User provided DBS balance
        ("DBS", 36000, 1089.79, 1)

    ]

    for card in cards:

        c.execute(
            """
            INSERT OR IGNORE INTO cards
            (name, balance, min_due, due_day)
            VALUES (?, ?, ?, ?)
            """,
            card
        )

    conn.commit()

    conn.close()


# ============================================================
# DATABASE READ FUNCTIONS
# ============================================================

def get_settings():

    conn = db()

    rows = conn.execute(
        "SELECT key, value FROM settings"
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
        INSERT OR REPLACE INTO settings
        (key, value)
        VALUES (?, ?)
        """,
        (key, float(value))
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
        conn
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
        conn
    )

    conn.close()

    return df


def expenses_df():

    conn = db()

    df = pd.read_sql_query(
        """
        SELECT *
        FROM transactions
        ORDER BY txn_date DESC, id DESC
        """,
        conn
    )

    conn.close()

    return df


def loan_payments_df():

    conn = db()

    df = pd.read_sql_query(
        """
        SELECT
            lp.*,
            l.name
        FROM loan_payments lp
        LEFT JOIN loans l
        ON lp.loan_id = l.id
        ORDER BY lp.pay_date DESC, lp.id DESC
        """,
        conn
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
        ON cc.card_id = c.id
        ORDER BY cc.cycle_date DESC, cc.id DESC
        """,
        conn
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

st.sidebar.title("⚙️ Financial Controls")

st.sidebar.caption(
    "Change your real numbers here. "
    "The entire plan recalculates automatically."
)


# ============================================================
# INCOME
# ============================================================

with st.sidebar.expander(
    "💰 Income & Cash",
    expanded=True
):

    salary = st.number_input(
        "Monthly take-home salary",
        min_value=0.0,
        value=float(settings["salary"]),
        step=1000.0
    )

    savings = st.number_input(
        "Current savings",
        min_value=0.0,
        value=float(settings["savings"]),
        step=1000.0
    )

    bonus = st.number_input(
        "Bonus this month",
        min_value=0.0,
        value=float(settings["bonus"]),
        step=5000.0
    )

    annual_salary = st.number_input(
        "Annual salary",
        min_value=0.0,
        value=float(settings["annual_salary"]),
        step=10000.0
    )

    increment = st.number_input(
        "Expected increment %",
        min_value=0.0,
        value=float(settings["increment_pct"]),
        step=1.0
    )

    if st.button(
        "Save income",
        use_container_width=True
    ):

        set_setting("salary", salary)
        set_setting("savings", savings)
        set_setting("bonus", bonus)
        set_setting("annual_salary", annual_salary)
        set_setting("increment_pct", increment)

        st.success("Income updated.")

        st.rerun()


# ============================================================
# EXPENSE SETTINGS
# ============================================================

with st.sidebar.expander(
    "🏠 Monthly Living Expenses"
):

    living_inputs = {}

    items = [

        ("rent", "Rent"),

        ("fuel", "Fuel"),

        ("groceries", "Groceries"),

        ("misc", "Miscellaneous"),

        ("jio", "JioFiber"),

        ("salon", "Salon"),

    ]

    for key, label in items:

        living_inputs[key] = st.number_input(
            label,
            min_value=0.0,
            value=float(settings[key]),
            step=100.0
        )

    if st.button(
        "Save expenses",
        use_container_width=True
    ):

        for key, value in living_inputs.items():

            set_setting(
                key,
                value
            )

        st.success(
            "Living expenses updated."
        )

        st.rerun()


# ============================================================
# DEBT SETTINGS
# ============================================================

with st.sidebar.expander(
    "💳 Debt Settings"
):

    cheq_fee = st.number_input(
        "CheQ fee per card",
        min_value=0.0,
        value=float(
            settings["cheq_fee_per_card"]
        ),
        step=100.0
    )

    emergency_buffer = st.number_input(
        "Minimum cash buffer",
        min_value=0.0,
        value=float(
            settings["emergency_buffer"]
        ),
        step=1000.0
    )

    if st.button(
        "Save debt settings",
        use_container_width=True
    ):

        set_setting(
            "cheq_fee_per_card",
            cheq_fee
        )

        set_setting(
            "emergency_buffer",
            emergency_buffer
        )

        st.success(
            "Debt settings updated."
        )

        st.rerun()


# ============================================================
# REFRESH DATA
# ============================================================

settings = get_settings()

loans = loans_df()

cards = cards_df()

active_loans = loans[
    loans["active"] == 1
].copy()

active_cards = cards[
    cards["active"] == 1
].copy()


# ============================================================
# CORE CALCULATIONS
# ============================================================

monthly_emi = float(
    active_loans["emi"].sum()
)

living_cost = sum(
    settings[key]
    for key in [
        "rent",
        "fuel",
        "groceries",
        "misc",
        "jio",
        "salon"
    ]
)

card_balance = float(
    active_cards["balance"].sum()
)

card_minimum = float(
    active_cards["min_due"].sum()
)

salary = float(
    settings["salary"]
)

monthly_required = (
    living_cost
    +
    monthly_emi
)

monthly_shortage = (
    monthly_required
    -
    salary
)


expected_annual = (
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
    expected_annual
    /
    12
)


# ============================================================
# HEADER
# ============================================================

st.title(
    "💰 Debt Escape Manager"
)

st.caption(
    "Your goal: survive the debt bridge without taking another loan."
)


# ============================================================
# TOP METRICS
# ============================================================

c1, c2, c3, c4 = st.columns(4)

c1.metric(
    "Salary",
    money(salary)
)

c2.metric(
    "Monthly EMIs",
    money(monthly_emi)
)

c3.metric(
    "Living Costs",
    money(living_cost)
)

if monthly_shortage > 0:

    c4.metric(
        "Monthly Shortage",
        money(monthly_shortage)
    )

else:

    c4.metric(
        "Monthly Surplus",
        money(abs(monthly_shortage))
    )


# ============================================================
# TABS
# ============================================================

tabs = st.tabs(
    [
        "🚨 NO NEW LOAN PLAN",
        "🏠 Daily Decision",
        "🏦 Loans",
        "💳 Cards + CheQ",
        "💸 Expenses",
        "📈 Forecast",
        "⚙️ Data"
    ]
)


# ============================================================
# TAB 1
# NO NEW LOAN PLAN
# ============================================================

with tabs[0]:

    st.header(
        "🚨 No-New-Loan Plan"
    )

    st.caption(
        "This is the most important screen. "
        "It answers: 'How do I survive the shortage without taking another loan?'"
    )


    # --------------------------------------------------------
    # CURRENT STRUCTURAL GAP
    # --------------------------------------------------------

    if monthly_shortage > 0:

        st.error(
            f"""
            You currently have a structural shortage of
            **{money(monthly_shortage)} per month.**

            Salary: {money(salary)}

            Living costs: {money(living_cost)}

            EMIs: {money(monthly_emi)}

            The objective is NOT to solve the entire shortage with
            another loan.

            The objective is to bridge the next few months until
            your EMIs naturally disappear.
            """
        )

    else:

        st.success(
            f"""
            Your salary currently covers your living expenses
            and scheduled EMIs.

            Current surplus:
            **{money(abs(monthly_shortage))}**
            """
        )


    # ========================================================
    # MONTH-BY-MONTH BRIDGE
    # ========================================================

    st.subheader(
        "📅 Your shortage will reduce as loans finish"
    )


    max_months = max(
        24,
        int(
            active_loans[
                "pending_months"
            ].max()
        )
        if not active_loans.empty
        else 24
    )


    bridge_rows = []

    cumulative_shortage = 0

    turning_point = None


    for month in range(
        1,
        max_months + 1
    ):

        emi_for_month = float(
            active_loans.loc[
                active_loans[
                    "pending_months"
                ] >= month,
                "emi"
            ].sum()
        )


        monthly_cash_flow = (
            salary
            -
            living_cost
            -
            emi_for_month
        )


        if monthly_cash_flow < 0:

            shortage = abs(
                monthly_cash_flow
            )

        else:

            shortage = 0


        cumulative_shortage += shortage


        if (
            turning_point is None
            and
            monthly_cash_flow >= 0
        ):

            turning_point = month


        bridge_rows.append(
            {
                "Month": month,

                "EMIs": emi_for_month,

                "Cash Flow": monthly_cash_flow,

                "Shortage": shortage,

                "Cumulative Bridge Needed":
                    cumulative_shortage
            }
        )


    bridge = pd.DataFrame(
        bridge_rows
    )


    # --------------------------------------------------------
    # TURNING POINT
    # --------------------------------------------------------

    if turning_point:

        turning_emi = float(
            bridge.loc[
                bridge["Month"]
                ==
                turning_point,
                "EMIs"
            ].iloc[0]
        )

        turning_surplus = (
            salary
            -
            living_cost
            -
            turning_emi
        )


        st.success(
            f"""
            🎯 **Turning point: Month {turning_point}**

            At that point your scheduled EMI burden falls to
            approximately **{money(turning_emi)}**.

            Your monthly cash flow becomes approximately:

            **+{money(turning_surplus)}**

            This means the current shortage is a temporary
            bridge problem — provided you don't add another EMI.
            """
        )


    # --------------------------------------------------------
    # FIRST 6 MONTHS
    # --------------------------------------------------------

    first_six = bridge[
        bridge["Month"] <= 6
    ].copy()


    total_bridge = float(
        first_six[
            "Shortage"
        ].sum()
    )


    st.metric(
        "Estimated shortage to bridge over first 6 months",
        money(total_bridge)
    )


    display_bridge = first_six.copy()


    display_bridge[
        "EMIs"
    ] = display_bridge[
        "EMIs"
    ].apply(money)


    display_bridge[
        "Cash Flow"
    ] = display_bridge[
        "Cash Flow"
    ].apply(money)


    display_bridge[
        "Shortage"
    ] = display_bridge[
        "Shortage"
    ].apply(money)


    display_bridge[
        "Cumulative Bridge Needed"
    ] = display_bridge[
        "Cumulative Bridge Needed"
    ].apply(money)


    st.dataframe(
        display_bridge,
        hide_index=True,
        use_container_width=True
    )


    # ========================================================
    # THIS MONTH CASH
    # ========================================================

    st.subheader(
        "💵 This Month — Where will the money come from?"
    )


    total_cash = (
        settings["savings"]
        +
        settings["salary"]
        +
        settings["bonus"]
    )


    friend_payment = settings[
        "friend_loan"
    ]


    cash_after_friend = (
        total_cash
        -
        friend_payment
    )


    cash_after_living = (
        cash_after_friend
        -
        living_cost
    )


    cash_after_emi = (
        cash_after_living
        -
        monthly_emi
    )


    cash_after_minimums = (
        cash_after_emi
        -
        card_minimum
    )


    this_month = pd.DataFrame(
        [
            [
                "Starting savings",
                settings["savings"]
            ],

            [
                "Salary",
                settings["salary"]
            ],

            [
                "Bonus",
                settings["bonus"]
            ],

            [
                "Friend loan",
                -friend_payment
            ],

            [
                "Living expenses",
                -living_cost
            ],

            [
                "EMIs",
                -monthly_emi
            ],

            [
                "Card minimums",
                -card_minimum
            ],

            [
                "Cash remaining",
                cash_after_minimums
            ]
        ],
        columns=[
            "Item",
            "Amount"
        ]
    )


    this_month[
        "Amount"
    ] = this_month[
        "Amount"
    ].apply(money)


    st.dataframe(
        this_month,
        hide_index=True,
        use_container_width=True
    )


    # ========================================================
    # EXACT MONTHLY ACTION
    # ========================================================

    st.subheader(
        "🎯 What you should do"
    )


    if cash_after_minimums < 0:

        st.error(
            f"""
            🔴 **DO NOT MAKE EXTRA DEBT PAYMENTS THIS MONTH.**

            You are approximately
            **{money(abs(cash_after_minimums))}**
            short after:

            • Friend loan
            • Living expenses
            • EMIs
            • Card minimums

            Making an extra payment would probably force you
            to borrow again.

            Your priority is simply to survive this month.
            """
        )

    elif cash_after_minimums < settings[
        "emergency_buffer"
    ]:

        st.warning(
            f"""
            🟠 Keep your remaining
            **{money(cash_after_minimums)}**
            as cash.

            Do not make an aggressive debt payment.

            You need liquidity to prevent another loan.
            """
        )

    else:

        available = (
            cash_after_minimums
            -
            settings["emergency_buffer"]
        )


        st.success(
            f"""
            🟢 You can potentially use
            **{money(available)}**
            for debt reduction after maintaining your
            {money(settings["emergency_buffer"])}
            cash buffer.
            """
        )


    # ========================================================
    # HOW TO BRIDGE
    # ========================================================

    st.subheader(
        "🛟 How to bridge the shortage"
    )


    # Suggested cuts
    salon_cut = min(
        settings["salon"],
        2000
    )

    misc_cut = min(
        settings["misc"],
        1000
    )

    grocery_cut = min(
        settings["groceries"] * 0.25,
        500
    )


    possible_cuts = (
        salon_cut
        +
        misc_cut
        +
        grocery_cut
    )


    st.markdown(
        f"""
        ### Step 1 — Reduce discretionary spending temporarily

        Suggested temporary cuts:

        • Salon: **{money(salon_cut)}**

        • Miscellaneous: **{money(misc_cut)}**

        • Groceries: **{money(grocery_cut)}**

        Potential monthly reduction:
        **{money(possible_cuts)}**

        This is not meant to be permanent.
        The purpose is to survive the debt bridge.
        """
    )


    reduced_shortage = max(
        0,
        monthly_shortage
        -
        possible_cuts
    )


    st.info(
        f"""
        After these suggested cuts, your monthly shortage could
        fall from {money(monthly_shortage)}
        to approximately **{money(reduced_shortage)}**.
        """
    )


    # ========================================================
    # CHEQ OPTIONS
    # ========================================================

    st.subheader(
        "💳 If you absolutely need card rotation"
    )


    options = []


    for number in range(
        0,
        len(active_cards) + 1
    ):

        fee = (
            number
            *
            settings["cheq_fee_per_card"]
        )


        if number == 0:

            description = (
                "No card rotation"
            )

        else:

            description = (
                f"Rotate {number} card"
                +
                ("s" if number > 1 else "")
            )


        options.append(
            {
                "Option": description,

                "CheQ Fee": fee,

                "Extra Cost": fee
            }
        )


    cheq_df = pd.DataFrame(
        options
    )


    cheq_df[
        "CheQ Fee"
    ] = cheq_df[
        "CheQ Fee"
    ].apply(money)


    cheq_df[
        "Extra Cost"
    ] = cheq_df[
        "Extra Cost"
    ].apply(money)


    st.dataframe(
        cheq_df,
        hide_index=True,
        use_container_width=True
    )


    st.warning(
        """
        **Rule:**

        Use the minimum number of cards necessary.

        Do NOT automatically rotate all three cards.

        Every additional card costs approximately ₹2,000 in your
        current CheQ setup.
        """
    )


    # ========================================================
    # FUTURE FREED EMI
    # ========================================================

    st.subheader(
        "🚀 Your upcoming breathing room"
    )


    future = active_loans[
        active_loans[
            "pending_months"
        ] <= 12
    ].sort_values(
        "pending_months"
    )


    for _, row in future.iterrows():

        st.markdown(
            f"""
            **{row["name"]}**

            {int(row["pending_months"])} month(s) left

            → {money(row["emi"])}
            monthly EMI will disappear.
            """
        )


    st.success(
        """
        **Golden rule:**

        When an EMI disappears, do NOT increase spending.

        Redirect the entire EMI toward your credit-card/CheQ debt.

        That is how the temporary shortage becomes a permanent
        surplus.
        """
    )


# ============================================================
# TAB 2
# DAILY DECISION
# ============================================================

with tabs[1]:

    st.header(
        "🏠 Daily Financial Decision"
    )

    st.caption(
        "Use this before spending or borrowing."
    )


    # --------------------------------------------------------
    # SAFE SPENDING
    # --------------------------------------------------------

    st.subheader(
        "💰 Can I spend this money?"
    )


    requested_spend = st.number_input(
        "Amount I want to spend",
        min_value=0.0,
        step=100.0,
        key="spend_check"
    )


    # Basic safe spending calculation
    safe_cash = (
        settings["savings"]
        -
        settings["emergency_buffer"]
    )


    if requested_spend > 0:

        if safe_cash >= requested_spend:

            st.success(
                f"""
                🟢 This expense is affordable from your current
                savings buffer.

                After spending:

                **{money(safe_cash - requested_spend)}**
                would remain above your minimum buffer.
                """
            )

        else:

            st.error(
                f"""
                🔴 I would NOT recommend this expense right now.

                Your usable cash above the emergency buffer is only
                {money(max(0, safe_cash))}.

                Spending {money(requested_spend)} would increase
                the probability of needing card/CheQ borrowing.
                """
            )


    # ========================================================
    # MONEY AVAILABLE DECISION
    # ========================================================

    st.subheader(
        "💵 I received extra money — what should I do?"
    )


    extra_money = st.number_input(
        "Extra money available",
        min_value=0.0,
        step=1000.0,
        key="extra_money"
    )


    if extra_money > 0:

        if monthly_shortage > 0:

            st.warning(
                f"""
                **Recommendation: KEEP THE MONEY.**

                Your current monthly cash flow is negative by
                {money(monthly_shortage)}.

                Until your monthly cash flow becomes positive,
                extra money should primarily be used to prevent
                new borrowing.

                Suggested use:

                1. Keep emergency buffer.
                2. Cover upcoming EMI shortage.
                3. Avoid large early repayments.
                """
            )

        else:

            debt_payment = max(
                0,
                extra_money
                -
                settings["emergency_buffer"]
            )


            st.success(
                f"""
                Your monthly cash flow is positive.

                Keep approximately
                {money(settings["emergency_buffer"])}
                as buffer.

                Potential debt payment:

                **{money(debt_payment)}**
                """
            )


    # ========================================================
    # NEW LOAN DECISION
    # ========================================================

    st.subheader(
        "🚨 Should I take a new loan?"
    )


    new_loan_amount = st.number_input(
        "Loan amount",
        min_value=0.0,
        step=1000.0,
        key="new_loan_amount"
    )


    new_loan_emi = st.number_input(
        "New monthly EMI",
        min_value=0.0,
        step=100.0,
        key="new_loan_emi"
    )


    if new_loan_amount > 0:

        new_gap = (
            monthly_shortage
            +
            new_loan_emi
        )


        if monthly_shortage > 0:

            st.error(
                f"""
                🔴 **DO NOT TAKE THIS LOAN unless it is genuinely
                unavoidable.**

                You already have a monthly shortage of
                {money(monthly_shortage)}.

                This loan would add another
                {money(new_loan_emi)}
                every month.

                Your new structural shortage would be approximately:

                **{money(new_gap)} / month**

                Your current problem is already temporary because
                several existing loans are ending.
                """
            )

        else:

            st.warning(
                f"""
                🟠 Your current salary covers your existing
                commitments, but this loan would add
                {money(new_loan_emi)}
                per month.

                Avoid it unless the borrowing has a clear,
                necessary purpose.
                """
            )


# ============================================================
# TAB 3
# LOANS
# ============================================================

with tabs[2]:

    st.header(
        "🏦 Loans"
    )


    display = active_loans.copy()


    display[
        "Monthly EMI"
    ] = display[
        "emi"
    ].apply(money)


    display[
        "Remaining EMI Outflow"
    ] = (
        active_loans["emi"]
        *
        active_loans[
            "pending_months"
        ]
    ).apply(money)


    display = display[
        [
            "name",
            "Monthly EMI",
            "pending_months",
            "emi_day",
            "Remaining EMI Outflow"
        ]
    ]


    display.columns = [
        "Loan",
        "Monthly EMI",
        "Months Left",
        "EMI Day",
        "Remaining EMI Outflow"
    ]


    st.dataframe(
        display,
        hide_index=True,
        use_container_width=True
    )


    # ========================================================
    # RECORD PAYMENT
    # ========================================================

    st.subheader(
        "✅ I paid an EMI"
    )


    loan_map = dict(
        zip(
            active_loans["name"],
            active_loans["id"]
        )
    )


    if loan_map:

        with st.form(
            "loan_payment"
        ):

            selected_loan = st.selectbox(
                "Loan",
                list(
                    loan_map.keys()
                )
            )


            amount = st.number_input(
                "Amount paid",
                min_value=0.0,
                step=100.0
            )


            months = st.number_input(
                "Months reduced",
                min_value=1,
                max_value=60,
                value=1
            )


            note = st.text_input(
                "Note",
                "Regular EMI"
            )


            submit = st.form_submit_button(
                "Record payment"
            )


        if submit:

            conn = db()


            loan_id = loan_map[
                selected_loan
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
                    amount,
                    months,
                    note
                )
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

                            WHEN
                                pending_months - ?
                                <= 0

                            THEN 0

                            ELSE 1

                        END

                WHERE id = ?
                """,
                (
                    months,
                    months,
                    loan_id
                )
            )


            conn.commit()

            conn.close()


            st.success(
                f"{selected_loan} updated."
            )


            st.rerun()


    # ========================================================
    # NEW LOAN
    # ========================================================

    st.subheader(
        "➕ Add new loan"
    )


    with st.form(
        "new_loan"
    ):

        lender = st.text_input(
            "Lender"
        )


        loan_amount = st.number_input(
            "Loan amount",
            min_value=0.0,
            step=1000.0
        )


        new_emi = st.number_input(
            "Monthly EMI",
            min_value=0.0,
            step=100.0
        )


        months = st.number_input(
            "Months",
            min_value=1,
            max_value=120,
            value=6
        )


        reason = st.text_input(
            "Reason"
        )


        add = st.form_submit_button(
            "Add loan"
        )


    if add:

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
                    months,
                    reason
                )
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
                    months,
                    1,
                    0
                )
            )


            conn.commit()

            conn.close()


            st.success(
                "New loan added."
            )


            st.rerun()


# ============================================================
# TAB 4
# CARDS + CHEQ
# ============================================================

with tabs[3]:

    st.header(
        "💳 Credit Cards + CheQ"
    )


    st.warning(
        """
        Your strategy is different from normal card repayment.

        You pay the complete card bill and then use CheQ to
        recycle money back into your account.

        Therefore the app tracks:

        CARD PAYMENT

        ↓

        CHEQ RECYCLING

        ↓

        CHEQ FEE

        ↓

        TRUE DEBT
        """
    )


    card_display = active_cards.copy()


    card_display[
        "balance"
    ] = card_display[
        "balance"
    ].apply(money)


    card_display[
        "min_due"
    ] = card_display[
        "min_due"
    ].apply(money)


    card_display = card_display[
        [
            "name",
            "balance",
            "min_due",
            "due_day"
        ]
    ]


    card_display.columns = [
        "Card",
        "Balance",
        "Minimum Due",
        "Due Day"
    ]


    st.dataframe(
        card_display,
        hide_index=True,
        use_container_width=True
    )


    # ========================================================
    # RECORD ROTATION
    # ========================================================

    st.subheader(
        "🔄 Record card rotation"
    )


    card_map = dict(
        zip(
            active_cards["name"],
            active_cards["id"]
        )
    )


    if card_map:

        with st.form(
            "card_rotation"
        ):

            card = st.selectbox(
                "Card",
                list(
                    card_map.keys()
                )
            )


            bill = st.number_input(
                "Card bill paid",
                min_value=0.0,
                step=1000.0
            )


            recycled = st.number_input(
                "Amount received through CheQ",
                min_value=0.0,
                step=1000.0
            )


            fee = st.number_input(
                "CheQ fee",
                min_value=0.0,
                value=float(
                    settings[
                        "cheq_fee_per_card"
                    ]
                ),
                step=100.0
            )


            new_spend = st.number_input(
                "New card spending",
                min_value=0.0,
                step=500.0
            )


            note = st.text_input(
                "Note"
            )


            submit_cycle = st.form_submit_button(
                "Record rotation"
            )


        if submit_cycle:

            conn = db()


            card_id = card_map[
                card
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
                    bill,
                    recycled,
                    fee,
                    note
                )
            )


            # Approximate balance
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
                    bill,
                    new_spend,
                    card_id
                )
            )


            conn.commit()

            conn.close()


            st.success(
                "Card rotation recorded."
            )


            st.rerun()


    cycles = card_cycles_df()


    if not cycles.empty:

        total_fees = float(
            cycles[
                "cheq_fee"
            ].sum()
        )


        total_recycled = float(
            cycles[
                "recycled_amount"
            ].sum()
        )


        c1, c2 = st.columns(2)


        c1.metric(
            "CheQ Fees Paid",
            money(total_fees)
        )


        c2.metric(
            "Money Recycled",
            money(total_recycled)
        )


        st.subheader(
            "Card/CheQ history"
        )


        history = cycles.copy()


        for col in [
            "paid_amount",
            "recycled_amount",
            "cheq_fee"
        ]:

            history[col] = (
                history[col]
                .apply(money)
            )


        st.dataframe(
            history,
            hide_index=True,
            use_container_width=True
        )


# ============================================================
# TAB 5
# EXPENSES
# ============================================================

with tabs[4]:

    st.header(
        "💸 Expense Manager"
    )


    st.caption(
        "Record expenses as they actually happen."
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

        "Other"

    ]


    with st.form(
        "expense"
    ):

        expense_date = st.date_input(
            "Date",
            today
        )


        category = st.selectbox(
            "Category",
            categories
        )


        amount = st.number_input(
            "Amount",
            min_value=0.0,
            step=100.0
        )


        description = st.text_input(
            "Description"
        )


        add_expense = st.form_submit_button(
            "Add expense"
        )


    if add_expense:

        if amount > 0:

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
                    amount,
                    "expense",
                    description
                )
            )


            conn.commit()

            conn.close()


            st.success(
                "Expense recorded."
            )


            st.rerun()


    expenses = expenses_df()


    if not expenses.empty:

        expenses[
            "txn_date"
        ] = pd.to_datetime(
            expenses[
                "txn_date"
            ]
        )


        current_month = expenses[
            (
                expenses[
                    "txn_date"
                ].dt.month
                ==
                today.month
            )
            &
            (
                expenses[
                    "txn_date"
                ].dt.year
                ==
                today.year
            )
        ]


        if not current_month.empty:

            st.subheader(
                "📊 This month's actual spending"
            )


            spending = (
                current_month
                .groupby(
                    "category"
                )[
                    "amount"
                ]
                .sum()
                .sort_values(
                    ascending=False
                )
            )


            display_spending = (
                spending
                .reset_index()
            )


            display_spending[
                "amount"
            ] = display_spending[
                "amount"
            ].apply(money)


            st.dataframe(
                display_spending,
                hide_index=True,
                use_container_width=True
            )


            st.bar_chart(
                spending
            )


        st.subheader(
            "Recent expenses"
        )


        recent = expenses.head(
            30
        ).copy()


        recent[
            "amount"
        ] = recent[
            "amount"
        ].apply(money)


        st.dataframe(
            recent,
            hide_index=True,
            use_container_width=True
        )


# ============================================================
# TAB 6
# FORECAST
# ============================================================

with tabs[5]:

    st.header(
        "📈 Debt Escape Forecast"
    )


    max_months = max(
        36,
        int(
            active_loans[
                "pending_months"
            ].max()
        )
        if not active_loans.empty
        else 36
    )


    forecast_rows = []


    for month in range(
        1,
        max_months + 1
    ):

        emi = float(
            active_loans.loc[
                active_loans[
                    "pending_months"
                ] >= month,
                "emi"
            ].sum()
        )


        cash_flow = (
            salary
            -
            living_cost
            -
            emi
        )


        freed = (
            monthly_emi
            -
            emi
        )


        forecast_rows.append(
            {
                "Month": month,

                "EMI": emi,

                "Cash Flow": cash_flow,

                "EMI Freed": freed
            }
        )


    forecast = pd.DataFrame(
        forecast_rows
    )


    # --------------------------------------------------------
    # CHART
    # --------------------------------------------------------

    chart_data = forecast.set_index(
        "Month"
    )[
        [
            "EMI",
            "Cash Flow"
        ]
    ]


    st.line_chart(
        chart_data
    )


    # --------------------------------------------------------
    # TABLE
    # --------------------------------------------------------

    table = forecast.head(
        24
    ).copy()


    table[
        "EMI"
    ] = table[
        "EMI"
    ].apply(money)


    table[
        "Cash Flow"
    ] = table[
        "Cash Flow"
    ].apply(money)


    table[
        "EMI Freed"
    ] = table[
        "EMI Freed"
    ].apply(money)


    st.dataframe(
        table,
        hide_index=True,
        use_container_width=True
    )


    # --------------------------------------------------------
    # MILESTONES
    # --------------------------------------------------------

    st.subheader(
        "🎯 EMI milestones"
    )


    milestones = active_loans.sort_values(
        "pending_months"
    ).copy()


    milestones[
        "Monthly EMI"
    ] = milestones[
        "emi"
    ].apply(money)


    milestones[
        "Monthly Cash Freed"
    ] = milestones[
        "emi"
    ].apply(money)


    milestones = milestones[
        [
            "name",
            "Monthly EMI",
            "pending_months",
            "Monthly Cash Freed"
        ]
    ]


    milestones.columns = [
        "Loan",
        "EMI",
        "Months Left",
        "Cash Freed When Closed"
    ]


    st.dataframe(
        milestones,
        hide_index=True,
        use_container_width=True
    )


# ============================================================
# TAB 7
# DATA
# ============================================================

with tabs[6]:

    st.header(
        "⚙️ Data & Backup"
    )


    st.info(
        """
        Your history is stored in the local SQLite file:

        debt_manager.db

        Do not delete this file unless you want to reset your history.
        """
    )


    st.download_button(
        "Download Loans CSV",
        loans.to_csv(
            index=False
        ).encode("utf-8"),
        "loans.csv",
        "text/csv"
    )


    st.download_button(
        "Download Cards CSV",
        cards.to_csv(
            index=False
        ).encode("utf-8"),
        "cards.csv",
        "text/csv"
    )


    st.download_button(
        "Download Expenses CSV",
        expenses_df()
        .to_csv(
            index=False
        )
        .encode("utf-8"),
        "expenses.csv",
        "text/csv"
    )


    st.divider()


    st.warning(
        "Resetting deletes your local debt history."
    )


    if st.button(
        "Reset database",
        type="secondary"
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
    Debt Escape Manager is a budgeting and planning tool.
    Verify actual lender balances, interest, fees, due dates,
    card statements and CheQ charges before making payments.
    """
)
