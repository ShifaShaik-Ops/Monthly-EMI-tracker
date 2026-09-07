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
