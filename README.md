# Debt Manager Streamlit App

This app is designed around the user's actual debt situation, not just as a spreadsheet tracker.

## What it does

- Stores loans, cards, expenses and payment events in a local SQLite database.
- Recalculates monthly cash-flow after every update.
- Shows the structural monthly gap between income and living costs + EMIs.
- Separately tracks card bills paid vs. amounts recycled through CheQ.
- Tracks CheQ convenience fees.
- Lets you record each loan EMI/month completed so pending months automatically reduce.
- Lets you add a new loan in real time.
- Lets you record expenses as they happen.
- Shows a forecast of when EMIs disappear and how much cash flow is freed.
- Provides action-oriented suggestions rather than just balances.

## Starting data loaded

Income/cash:
- Monthly take-home: ₹59,000
- Savings: ₹40,000
- Bonus this month: ₹60,000
- Annual salary: ₹7,23,256
- Expected increment: 10%
- Friend loan to clear: ₹80,000

Living:
- Rent ₹15,000
- Fuel ₹2,000
- Groceries ₹2,000
- Misc ₹2,000
- JioFiber ₹1,200
- Salon ₹2,000

Loans:
Fibe 9890 x 7
Stashfin 4199 x 12
LazyPay 4000 x 1
Kredibee 9219 x 6
Branch 2488 x 5
Money View 3764 x 6
Poonawala Fincorp 6507 x 22
Instamoney 5616 x 3
Kissht 1583 x 9
Loan Tap 5276 x 2
Flexipay 6000 x 24

Cards:
- Axis ₹60,000 (minimum due is an estimate of ₹2,000; verify)
- HDFC ₹29,656, minimum ₹1,816
- DBS ₹36,000 (minimum entered as a planning estimate; verify)

CheQ:
- Default convenience fee: ₹2,000 per rotated card

## Run locally

1. Install Python 3.10+.
2. Open a terminal in this folder.
3. Run:

    pip install -r requirements.txt

4. Run:

    streamlit run app.py

5. Open the local URL Streamlit prints, usually http://localhost:8501

## Making it accessible from another device

For a personal setup, deploy the same folder to a Streamlit-compatible host. The SQLite file is local to the running instance, so for serious long-term use, replace SQLite with a cloud database.

## Important model rule

The app does NOT treat "card paid in full" as the same thing as "debt reduced" when a CheQ recycling event is recorded. That distinction is intentional because the user is using CheQ to move the paid card amount back into the bank account and pays a convenience fee.
