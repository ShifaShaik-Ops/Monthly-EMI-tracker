import streamlit as st
import sqlite3
from datetime import date, datetime
from pathlib import Path
import pandas as pd

APP_DIR = Path(__file__).parent
DB_PATH = APP_DIR / "debt_manager.db"

st.set_page_config(page_title="Debt Manager AI", page_icon="💰", layout="wide")

# -----------------------------
# Database
# -----------------------------
def db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = db()
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY, value REAL
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS loans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE, emi REAL, pending_months INTEGER,
        emi_day INTEGER, rotatable INTEGER DEFAULT 0,
        active INTEGER DEFAULT 1
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS cards (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE, balance REAL, min_due REAL,
        due_day INTEGER, active INTEGER DEFAULT 1
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        txn_date TEXT, category TEXT, amount REAL,
        kind TEXT, note TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS loan_payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        loan_id INTEGER, pay_date TEXT, amount REAL,
        months_reduced INTEGER, note TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS card_cycles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        card_id INTEGER, cycle_date TEXT, paid_amount REAL,
        recycled_amount REAL, cheq_fee REAL, note TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS new_debts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        debt_date TEXT, lender TEXT, amount REAL,
        monthly_payment REAL, months INTEGER, note TEXT
    )""")
    conn.commit()

    defaults = {
        "salary":59000,
        "annual_salary":723256,
        "increment_pct":10,
        "bonus":60000,
        "savings":40000,
        "friend_loan":80000,
        "rent":15000,
        "fuel":2000,
        "groceries":2000,
        "misc":2000,
        "jio":1200,
        "salon":2000,
        "cheq_fee_per_card":2000,
        "emergency_buffer":10000,
    }
    for k,v in defaults.items():
        c.execute("INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)",(k,v))

    loans = [
        ("Fibe",9890,7,4,0),
        ("Stashfin",4199,12,2,1),
        ("LazyPay",4000,1,3,1),
        ("Kredibee",9219,6,2,0),
        ("Branch",2488,5,28,0),
        ("Money View",3764,6,3,0),
        ("Poonawala Fincorp",6507,22,5,0),
        ("Instamoney",5616,3,1,1),
        ("Kissht",1583,9,7,0),
        ("Loan Tap",5276,2,1,0),
        ("Flexipay",6000,24,26,0),
    ]
    for row in loans:
        c.execute("""INSERT OR IGNORE INTO loans
        (name,emi,pending_months,emi_day,rotatable) VALUES(?,?,?,?,?)""",row)

    cards = [
        ("Axis",60000,2000,0),
        ("HDFC",29656,1816,28),
        ("DBS",36000,1089.79,1),
    ]
    for row in cards:
        c.execute("""INSERT OR IGNORE INTO cards
        (name,balance,min_due,due_day) VALUES(?,?,?,?)""",row)
    conn.commit()
    conn.close()

def get_settings():
    conn=db()
    rows=conn.execute("SELECT key,value FROM settings").fetchall()
    conn.close()
    return {r["key"]:r["value"] for r in rows}

def set_setting(k,v):
    conn=db()
    conn.execute("INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)",(k,float(v)))
    conn.commit(); conn.close()

def loans_df():
    conn=db()
    df=pd.read_sql_query("SELECT * FROM loans ORDER BY emi DESC",conn)
    conn.close()
    return df

def cards_df():
    conn=db()
    df=pd.read_sql_query("SELECT * FROM cards ORDER BY balance DESC",conn)
    conn.close()
    return df

def payments_df():
    conn=db()
    df=pd.read_sql_query("""SELECT lp.*, l.name FROM loan_payments lp
                            LEFT JOIN loans l ON l.id=lp.loan_id
                            ORDER BY pay_date DESC, id DESC""",conn)
    conn.close()
    return df

def card_cycles_df():
    conn=db()
    df=pd.read_sql_query("""SELECT cc.*, c.name FROM card_cycles cc
                            LEFT JOIN cards c ON c.id=cc.card_id
                            ORDER BY cycle_date DESC, id DESC""",conn)
    conn.close()
    return df

def txns_df():
    conn=db()
    df=pd.read_sql_query("SELECT * FROM transactions ORDER BY txn_date DESC, id DESC",conn)
    conn.close()
    return df

init_db()
s=get_settings()
today=date.today()

# -----------------------------
# Calculations
# -----------------------------
loans=loans_df()
cards=cards_df()
loan_emi=float(loans.loc[loans.active==1,"emi"].sum())
loan_estimated_outstanding=float((loans.loc[loans.active==1,"emi"]*loans.loc[loans.active==1,"pending_months"]).sum())
living=s["rent"]+s["fuel"]+s["groceries"]+s["misc"]+s["jio"]+s["salon"]
card_balance=float(cards.loc[cards.active==1,"balance"].sum())
card_min=float(cards.loc[cards.active==1,"min_due"].sum())
cheq_all=s["cheq_fee_per_card"]*len(cards[cards.active==1])
monthly_burn=loan_emi+living
monthly_gap=monthly_burn-s["salary"]
expected_monthly_gross=(s["annual_salary"]*(1+s["increment_pct"]/100))/12
cash_now=s["savings"]+s["salary"]+s["bonus"]
after_friend=cash_now-s["friend_loan"]
after_month=after_friend-living-loan_emi-card_min

# -----------------------------
# Sidebar
# -----------------------------
st.sidebar.title("⚙️ Your controls")
st.sidebar.caption("Everything is editable. The app recalculates after every save.")

with st.sidebar.expander("Income & cash", expanded=True):
    salary=st.number_input("Monthly take-home", min_value=0.0, value=float(s["salary"]), step=1000.0)
    savings=st.number_input("Current savings", min_value=0.0, value=float(s["savings"]), step=1000.0)
    bonus=st.number_input("Bonus this month", min_value=0.0, value=float(s["bonus"]), step=5000.0)
    annual=st.number_input("Annual salary", min_value=0.0, value=float(s["annual_salary"]), step=10000.0)
    inc=st.number_input("Expected increment %", min_value=0.0, value=float(s["increment_pct"]), step=1.0)
    if st.button("Save income"):
        for k,v in [("salary",salary),("savings",savings),("bonus",bonus),("annual_salary",annual),("increment_pct",inc)]:
            set_setting(k,v)
        st.rerun()

with st.sidebar.expander("Living expenses", expanded=False):
    vals={}
    for k,label in [("rent","Rent"),("fuel","Fuel"),("groceries","Groceries"),("misc","Misc"),("jio","JioFiber"),("salon","Salon")]:
        vals[k]=st.number_input(label,min_value=0.0,value=float(s[k]),step=100.0)
    if st.button("Save living costs"):
        for k,v in vals.items(): set_setting(k,v)
        st.rerun()

with st.sidebar.expander("Debt rules", expanded=False):
    fee=st.number_input("CheQ fee per rotated card",min_value=0.0,value=float(s["cheq_fee_per_card"]),step=100.0)
    buffer=st.number_input("Minimum cash buffer",min_value=0.0,value=float(s["emergency_buffer"]),step=1000.0)
    if st.button("Save debt rules"):
        set_setting("cheq_fee_per_card",fee); set_setting("emergency_buffer",buffer)
        st.rerun()

# -----------------------------
# Header + insight engine
# -----------------------------
st.title("💰 Debt Manager — Real Cash Flow & Exit Plan")
st.caption("This is an action dashboard, not just a tracker. Record what actually happened and the recommendations change.")

# Refresh calculations after sidebar edits
s=get_settings()
loans=loans_df(); cards=cards_df()
loan_emi=float(loans.loc[loans.active==1,"emi"].sum())
loan_estimated_outstanding=float((loans.loc[loans.active==1,"emi"]*loans.loc[loans.active==1,"pending_months"]).sum())
living=sum(s[k] for k in ["rent","fuel","groceries","misc","jio","salon"])
card_balance=float(cards.loc[cards.active==1,"balance"].sum())
card_min=float(cards.loc[cards.active==1,"min_due"].sum())
cheq_all=s["cheq_fee_per_card"]*len(cards[cards.active==1])
monthly_gap=loan_emi+living-s["salary"]
expected_monthly_gross=(s["annual_salary"]*(1+s["increment_pct"]/100))/12
cash_now=s["savings"]+s["salary"]+s["bonus"]
after_friend=cash_now-s["friend_loan"]
after_month=after_friend-living-loan_emi-card_min

# Insights
st.subheader("🔎 What your numbers are saying now")
alerts=[]
if monthly_gap>0:
    alerts.append(("🔴",f"Your salary is about ₹{monthly_gap:,.0f} short of living costs + EMIs each month. This is the core reason card/CheQ rotation is happening."))
else:
    alerts.append(("🟢",f"Your salary covers living costs + scheduled EMIs with about ₹{-monthly_gap:,.0f} left."))
if len(cards[cards.active==1])>0:
    alerts.append(("🟠",f"If all {len(cards[cards.active==1])} cards are rotated through CheQ, estimated fees are ₹{cheq_all:,.0f} per cycle. This is a cost, not debt repayment."))
if after_month<0:
    alerts.append(("🔴",f"After clearing the ₹{s['friend_loan']:,.0f} friend loan, this month's cash plan is about ₹{abs(after_month):,.0f} short after living costs, EMIs and card minimums. Avoid an aggressive extra debt payment this month."))
if expected_monthly_gross> s["salary"]:
    alerts.append(("🟡",f"A 10% increment would make the stated annual salary about ₹{s['annual_salary']*(1+s['increment_pct']/100):,.0f}, or ₹{expected_monthly_gross:,.0f}/month gross. Treat this as upside until confirmed."))

for icon,msg in alerts:
    st.markdown(f"### {icon} {msg}")

c1,c2,c3,c4=st.columns(4)
c1.metric("Monthly EMIs",f"₹{loan_emi:,.0f}")
c2.metric("Living costs",f"₹{living:,.0f}")
c3.metric("Card balances",f"₹{card_balance:,.0f}")
c4.metric("Monthly structural gap",f"₹{monthly_gap:,.0f}",delta=f"-₹{monthly_gap:,.0f}" if monthly_gap>0 else None,delta_color="inverse")

# -----------------------------
# Tabs
# -----------------------------
tabs=st.tabs(["🏠 Action Plan","🏦 Loans","💳 Cards + CheQ","💸 Expenses","📈 Forecast","⚙️ Data"])

# Action plan
with tabs[0]:
    st.subheader("Your priority for the next 30 days")
    actions=[]
    if s["friend_loan"]>0:
        actions.append(("1","Clear friend loan","₹80,000 is a personal obligation you said you need to clear this month. Don't use the bonus to make a large card prepayment before this is handled."))
    actions.append(("2","Protect a cash buffer",f"Keep at least ₹{s['emergency_buffer']:,.0} available so a small surprise doesn't create another loan/card cycle."))
    actions.append(("3","Stop new card rotation where possible",f"Each rotated card costs about ₹{s['cheq_fee_per_card']:,.0} in CheQ fees. Record each rotation below."))
    actions.append(("4","Let short loans expire", "When a loan reaches 0 remaining months, redirect its old EMI to debt payoff. Do not add that amount to lifestyle spending."))
    actions.append(("5","Attack the revolving debt", "After the monthly cash flow becomes positive, direct the freed EMI amount to the card/CheQ balance with the highest cost, while keeping every EMI current."))
    for n,title,desc in actions:
        st.markdown(f"**{n}. {title}** — {desc}")

    st.subheader("This-month cash simulation")
    sim=pd.DataFrame({
        "Item":["Starting savings","Salary","Bonus","Friend loan","Living costs","Scheduled EMIs","Card minimums"],
        "Amount":[s["savings"],s["salary"],s["bonus"],-s["friend_loan"],-living,-loan_emi,-card_min]
    })
    sim.loc[len(sim)] = ["Estimated cash after mandatory items","",]
    sim.at[len(sim)-1,"Amount"]=sim["Amount"].sum()
    st.dataframe(sim,hide_index=True,use_container_width=True)
    st.info(f"Estimated cash after these mandatory items: ₹{sim['Amount'].sum():,.0f}. This does not assume extra card payment or CheQ recycling.")

# Loans
with tabs[1]:
    st.subheader("Loans — update the real status after every payment")
    st.caption("Pending-month estimates are planning values. Actual foreclosure/outstanding can differ because of interest and fees.")
    edit=loans.copy()
    edit["Estimated remaining EMI outflow"]=edit["emi"]*edit["pending_months"]
    st.dataframe(edit[["id","name","emi","pending_months","emi_day","rotatable","Estimated remaining EMI outflow"]],hide_index=True,use_container_width=True)

    st.markdown("### Record a loan payment / month completed")
    loan_names=dict(zip(loans["name"],loans["id"]))
    with st.form("loan_payment_form"):
        l_name=st.selectbox("Loan",list(loan_names.keys()))
        amount=st.number_input("Amount actually paid",min_value=0.0,step=100.0)
        months_red=st.number_input("Months reduced",min_value=0,max_value=60,value=1,step=1)
        note=st.text_input("Note","Regular EMI")
        submit=st.form_submit_button("Record payment")
    if submit:
        conn=db()
        lid=loan_names[l_name]
        conn.execute("INSERT INTO loan_payments(loan_id,pay_date,amount,months_reduced,note) VALUES(?,?,?,?,?)",
                     (lid,str(today),amount,months_red,note))
        conn.execute("UPDATE loans SET pending_months=MAX(0,pending_months-?), active=CASE WHEN pending_months-?<=0 THEN 0 ELSE 1 END WHERE id=?",
                     (months_red,months_red,lid))
        conn.commit(); conn.close()
        st.success(f"Recorded ₹{amount:,.0f} for {l_name}.")
        st.rerun()

    st.markdown("### Take a new loan")
    with st.form("new_loan_form"):
        nl=st.text_input("Lender")
        na=st.number_input("New loan amount",min_value=0.0,step=1000.0)
        ne=st.number_input("New monthly EMI",min_value=0.0,step=100.0)
        nm=st.number_input("Number of months",min_value=1,max_value=120,value=6)
        nn=st.text_input("Reason")
        ns=st.form_submit_button("Add new loan")
    if ns and nl and na>0:
        conn=db()
        conn.execute("INSERT INTO new_debts(debt_date,lender,amount,monthly_payment,months,note) VALUES(?,?,?,?,?,?)",
                     (str(today),nl,na,ne,nm,nn))
        conn.execute("INSERT OR IGNORE INTO loans(name,emi,pending_months,emi_day,rotatable) VALUES(?,?,?,?,?)",
                     (nl,ne,nm,1,0))
        conn.commit(); conn.close()
        st.success("New debt added.")
        st.rerun()

    hist=payments_df()
    if not hist.empty:
        st.markdown("### Recent loan payments")
        st.dataframe(hist.head(15),hide_index=True,use_container_width=True)

# Cards + CheQ
with tabs[2]:
    st.subheader("Cards — distinguish paid cards from actual debt reduction")
    st.warning("If you pay a card in full and then use CheQ to recycle the amount, record the recycled amount here. The card may show ₹0, but your financial debt has not fallen by that amount.")
    st.dataframe(cards[["id","name","balance","min_due","due_day"]],hide_index=True,use_container_width=True)

    card_names=dict(zip(cards["name"],cards["id"]))
    with st.form("card_cycle"):
        cn=st.selectbox("Card",list(card_names.keys()))
        paid=st.number_input("Card bill paid",min_value=0.0,step=1000.0)
        recycled=st.number_input("Amount recycled back via CheQ",min_value=0.0,step=1000.0)
        fee=st.number_input("CheQ convenience fee",min_value=0.0,value=float(s["cheq_fee_per_card"]),step=100.0)
        new_spend=st.number_input("New card spending after payment",min_value=0.0,step=500.0)
        cnote=st.text_input("Cycle note")
        cs=st.form_submit_button("Record card cycle")
    if cs:
        conn=db()
        cid=card_names[cn]
        conn.execute("""INSERT INTO card_cycles(card_id,cycle_date,paid_amount,recycled_amount,cheq_fee,note)
                        VALUES(?,?,?,?,?,?)""",(cid,str(today),paid,recycled,fee,cnote))
        # Closing card balance approximation:
        conn.execute("UPDATE cards SET balance=MAX(0,balance-?+?) WHERE id=?",(paid,new_spend,cid))
        conn.commit(); conn.close()
        st.success("Card cycle recorded. Check the Insights tab and total debt again.")
        st.rerun()

    cc=card_cycles_df()
    if not cc.empty:
        st.markdown("### Card/CheQ history")
        st.dataframe(cc.head(20),hide_index=True,use_container_width=True)
        st.metric("Recorded CheQ fees",f"₹{cc['cheq_fee'].sum():,.0f}")
        st.metric("Recorded recycled amount",f"₹{cc['recycled_amount'].sum():,.0f}")

# Expenses
with tabs[3]:
    st.subheader("Real-time expense entry")
    cats=["Rent","Fuel","Groceries","Misc","JioFiber","Salon","Medical","Travel","Shopping","Food","Other"]
    with st.form("expense_form"):
        td=st.date_input("Date",today)
        cat=st.selectbox("Category",cats)
        amt=st.number_input("Amount",min_value=0.0,step=100.0)
        note=st.text_input("Description")
        es=st.form_submit_button("Add expense")
    if es and amt>0:
        conn=db()
        conn.execute("INSERT INTO transactions(txn_date,category,amount,kind,note) VALUES(?,?,?,?,?)",
                     (str(td),cat,amt,"expense",note))
        conn.commit(); conn.close()
        st.success("Expense added.")
        st.rerun()

    tx=txns_df()
    if not tx.empty:
        st.markdown("### Spending this month")
        tx["txn_date"]=pd.to_datetime(tx["txn_date"])
        m=tx[(tx["txn_date"].dt.year==today.year)&(tx["txn_date"].dt.month==today.month)]
        if not m.empty:
            bycat=m.groupby("category")["amount"].sum().sort_values(ascending=False).reset_index()
            st.dataframe(bycat,hide_index=True,use_container_width=True)
            st.bar_chart(bycat.set_index("category"))
        st.markdown("### Recent expenses")
        st.dataframe(tx.head(30),hide_index=True,use_container_width=True)

# Forecast
with tabs[4]:
    st.subheader("📈 Debt escape forecast")
    st.caption("This forecast uses your stated EMI durations. It is a planning model, not a lender payoff quote.")
    max_m=int(max(36, loans["pending_months"].max()+3))
    rows=[]
    temp=loans.copy()
    temp=temp[temp.active==1].copy()
    for m in range(1,max_m+1):
        emi_this=float(temp.loc[temp["pending_months"]>=m,"emi"].sum())
        freed=float(loan_emi-emi_this)
        rows.append([m,emi_this,freed,max(0,emi_this+living-s["salary"])])
    f=pd.DataFrame(rows,columns=["Month","Scheduled EMIs","EMI freed vs today","Cash-flow gap before card/CheQ"])
    st.line_chart(f.set_index("Month")[["Scheduled EMIs","EMI freed vs today"]])
    st.dataframe(f.head(24),hide_index=True,use_container_width=True)

    st.subheader("Which loans disappear first?")
    milestones=loans.sort_values("pending_months")[["name","emi","pending_months"]].copy()
    milestones["Monthly cash freed when closed"]=milestones["emi"]
    st.dataframe(milestones,hide_index=True,use_container_width=True)

    st.success("Strategy: every time a loan closes, redirect the full freed EMI to the revolving debt. If you spend the freed EMI, the debt-free date gets pushed out.")

# Data
with tabs[5]:
    st.subheader("Data & reset")
    st.caption("Your data is stored locally in debt_manager.db in the same folder as the app.")
    st.download_button("Download loan data CSV",loans.to_csv(index=False).encode("utf-8"),"loans.csv","text/csv")
    st.download_button("Download card data CSV",cards.to_csv(index=False).encode("utf-8"),"cards.csv","text/csv")
    st.download_button("Download expense data CSV",txns_df().to_csv(index=False).encode("utf-8"),"expenses.csv","text/csv")
    if st.button("Reset database to starting data",type="secondary"):
        if DB_PATH.exists():
            DB_PATH.unlink()
        st.rerun()

st.divider()
st.caption("Important: this app provides budgeting/decision support. Verify lender balances, due dates, interest, fees, and CheQ terms before making payments.")
