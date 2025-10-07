# Financial Tracker Application
# Created by: Bennett J. Richman
# Last Update: 10/07/25
# NOTE: Make sure to run 'pip install -r requirements.txt' in terminal if python packages not installed


# Libraries
import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, date
import altair as alt
from dateutil.relativedelta import relativedelta
import os
import json

# Page Config
st.set_page_config(page_title="Richman Finance Tracker", page_icon="💵", layout="centered")
SHEET_NAME = "Richman Finance Tracker"
TRANSACTIONS_SHEET = "Transactions"
BUDGETS_SHEET = "Budgets"
GOALS_SHEET = "Goals"

# Connect to Google Sheets + Drive (RW access)
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

# Authentication
@st.cache_resource(ttl=3600)
def get_gspread_client(spreadsheet_name=SHEET_NAME):
    """
    Create and Return an Authorized 'gspread' Client using the Service Account JSON.
    Load Credentials:
    # Local: service_account.json file in working directory
    # Streamlit Cloud: put the JSON content into a Secret called "gcp_service_account"
    """
    if "GCP_SERVICE_ACCOUNT" in st.secrets:
        # Streamlit Cloud Path: Secrets -> GCP_SERVICE_ACCOUNT (string contains JSON)
        info = st.secrets["GCP_SERVICE_ACCOUNT"]
        credentials = Credentials.from_service_account_info(info, scopes=SCOPES)
    elif os.path.exists("service_account.json"):
        credentials = Credentials.from_service_account_file("service_account.json", scopes=SCOPES)
    else:
        st.error("No Service Account Credentials found. Put service_account.json in this folder OR add GCP_SERVICE_ACCOUNT to Streamlit Secrets.")
        st.stop()

    client = gspread.authorize(credentials)

    # Debug: List all available sheets to ensure "Transactions" exists
    spreadsheet = client.open(spreadsheet_name)
    available_sheets = [sheet.title for sheet in spreadsheet.worksheets()]
    print(f"Available Sheets: {available_sheets}")  # Will show in terminal or Streamlit logs

    # Check if "Transactions" sheet exists
    if TRANSACTIONS_SHEET not in available_sheets:
        st.error(f"Sheet/tab '{TRANSACTIONS_SHEET}' not found in the spreadsheet '{spreadsheet_name}'. Available sheets: {available_sheets}")
        st.stop()
    
    return client

# Sheet Helper
@st.cache_data(ttl=60)
def load_sheet_dataframe(sheet_name, spreadsheet_name=SHEET_NAME):
    try:
        sheet = get_gspread_client(spreadsheet_name).open(spreadsheet_name).worksheet(sheet_name)
    except Exception as e:
        st.error(f"Unable to open sheet/tab '{sheet_name}' in spreadsheet '{spreadsheet_name}': {e}")
        st.stop()
    records = sheet.get_all_records()
    df = pd.DataFrame(records)
    return df, sheet

def append_transaction(row_values, spreadsheet_name=SHEET_NAME):
    _, ws = load_sheet_dataframe(TRANSACTIONS_SHEET, spreadsheet_name)
    ws.append_row(row_values, value_input_option="USER_ENTERED")

def update_budget_row(category, amount, spreadsheet_name=SHEET_NAME):
    df, ws = load_sheet_dataframe(BUDGETS_SHEET, spreadsheet_name)
    # if category exists, update row; else append
    if category in list(df["Category"].astype(str)):
        idx = df.index[df["Category"].astype(str) == category][0] + 2  # +2 because sheets are 1-indexed & header
        ws.update(f"B{idx}", float(amount))
    else:
        ws.append_row([category, float(amount)], value_input_option="USER_ENTERED")

def update_goal_row(goal_name, target, current, spreadsheet_name=SHEET_NAME):
    df, ws = load_sheet_dataframe(GOALS_SHEET, spreadsheet_name)
    if goal_name in list(df["Goal Name"].astype(str)):
        idx = df.index[df["Goal Name"].astype(str) == goal_name][0] + 2
        ws.update(f"B{idx}", float(target))
        ws.update(f"C{idx}", float(current))
    else:
        ws.append_row([goal_name, float(target), float(current)], value_input_option="USER_ENTERED")

# UI: Sidebar
st.sidebar.title("Family Finance")
st.sidebar.markdown("Quick links & Settings")
st.sidebar.markdown(f"**Spreadsheet:** {SHEET_NAME}")
st.sidebar.caption("Make sure the Service Account Email has edit access to the spreadsheet.")

# Spreadsheet Selector in Sidebar for selecting different Google Sheets
spreadsheet_name = st.sidebar.selectbox("Select Spreadsheet", ["Richman Finance Tracker", "Another Spreadsheet"])  # Add more sheets here

# Data Range Selector
today = date.today()
default_start = (today.replace(day=1) - relativedelta(months=0)).isoformat()
start_date = st.sidebar.date_input("Start date", value=datetime.fromisoformat(default_start))
end_date = st.sidebar.date_input("End date", value=today)

# Load Data from selected spreadsheet
transactions_df, transactions_ws = load_sheet_dataframe(TRANSACTIONS_SHEET, spreadsheet_name)
budgets_df, budgets_ws = load_sheet_dataframe(BUDGETS_SHEET, spreadsheet_name)
goals_df, goals_ws = load_sheet_dataframe(GOALS_SHEET, spreadsheet_name)

# Normalize dataframes
if transactions_df.empty:
    transactions_df = pd.DataFrame(columns=["Date","Category","Description","Amount","Payment Method","Notes"])
else:
    transactions_df["Date"] = pd.to_datetime(transactions_df["Date"])
    transactions_df["Amount"] = pd.to_numeric(transactions_df["Amount"], errors="coerce").fillna(0.0)

if budgets_df.empty:
    budgets_df = pd.DataFrame(columns=["Category","Monthly Budget"])
else:
    budgets_df["Monthly Budget"] = pd.to_numeric(budgets_df["Monthly Budget"], errors="coerce").fillna(0.0)

if goals_df.empty:
    goals_df = pd.DataFrame(columns=["Goal Name","Target Amount","Current Saved"])
else:
    goals_df["Target Amount"] = pd.to_numeric(goals_df["Target Amount"], errors="coerce").fillna(0.0)
    goals_df["Current Saved"] = pd.to_numeric(goals_df["Current Saved"], errors="coerce").fillna(0.0)

# Dashboard Layout
tab1, tab2, tab3, tab4 = st.tabs(["➕ Add Expense", "📊 Dashboard", "⚙️ Budgets", "🎯 Goals"])

# Tab 1 - Add Expense
with tab1:
    st.header("➕ Add New Expense")
    with st.form("add_expense_form", clear_on_submit=True):
        col1, col2 = st.columns([2,1])
        with col1:
            date_in = st.date_input("Date", value=today)
            category_in = st.selectbox("Category", options=sorted(set(list(budgets_df["Category"]) + ["Food","Utilities","Transportation","Entertainment","Other"])))
            desc_in = st.text_input("Description")
        with col2:
            amount_in = st.number_input("Amount ($)", min_value=0.0, format="%.2f")
            method_in = st.selectbox("Payment Method", options=["Amex","Visa","Checking","Cash","Other"])
            payer_in = st.selectbox("Payer", options=["You","Partner"])
        notes_in = st.text_area("Notes (optional)")
        submitted = st.form_submit_button("Add Expense")

        if submitted:
            # Build row and append
            row = [str(date_in), category_in, desc_in, float(amount_in), method_in, notes_in, payer_in]
            append_transaction(row)
            st.success(f"Added: {desc_in} — ${amount_in:.2f}")
            # Clear cache to reload updated data
            load_sheet_dataframe.clear()
            st.experimental_rerun()

# Tab 2 - Dashboard
with tab2:
    st.header("📊 Dashboard & Monthly Summary")

    if transactions_df.empty:
        st.info("No transactions yet. Add an expense in the 'Add Expense' tab.")
    else:
        # Filter by date range from sidebar
        mask = (transactions_df["Date"].dt.date >= start_date) & (transactions_df["Date"].dt.date <= end_date)
        df_filtered = transactions_df.loc[mask].copy()

        # Month selector or auto
        months = df_filtered["Date"].dt.to_period("M").astype(str).sort_values().unique()
        if len(months) == 0:
            st.info("No transactions in selected date range.")
        else:
            selected_month = st.selectbox("Select month", months, index=len(months)-1)
            df_month = df_filtered[df_filtered["Date"].dt.to_period("M").astype(str) == selected_month].copy()

            # Totals
            total_spent = df_month["Amount"].sum()
            incomes = 0.0  # placeholder if you later add income sheet
            remaining_total_budget = budgets_df["Monthly Budget"].sum() - total_spent

            col1, col2, col3 = st.columns(3)
            col1.metric("Total Spent", f"${total_spent:,.2f}")
            col2.metric("Total Budget (sum)", f"${budgets_df['Monthly Budget'].sum():,.2f}")
            col3.metric("Remaining vs Budgets", f"${remaining_total_budget:,.2f}")

            # Category breakdown
            cat_summary = df_month.groupby("Category")["Amount"].sum().reset_index().sort_values("Amount", ascending=False)

            st.subheader(f"Spending by Category — {selected_month}")
            bar = alt.Chart(cat_summary).mark_bar().encode(
                x=alt.X("sum(Amount):Q", title="Amount ($)"),
                y=alt.Y("Category:N", sort='-x'),
                tooltip=["Category","Amount"]
            ).properties(height=300)
            st.altair_chart(bar, use_container_width=True)

            # Budget comparison
            st.subheader("Budget vs Actual (per Category)")
            merged = pd.merge(cat_summary, budgets_df, on="Category", how="right").fillna(0)
            merged = merged.rename(columns={"Amount":"Spent", "Monthly Budget":"Budget"})
            merged["Spent"] = merged["Spent"].astype(float)
            merged["Budget"] = merged["Budget"].astype(float)
            merged["UsedPct"] = merged.apply(lambda r: 0 if r["Budget"] == 0 else min(100, (r["Spent"]/r["Budget"]*100)), axis=1)

            # Show table with progress bars
            for _, row in merged.sort_values("UsedPct", ascending=False).iterrows():
                name = row["Category"]
                spent = row["Spent"]
                bud = row["Budget"]
                pct = int(row["UsedPct"])
                colA, colB = st.columns([3,1])
                with colA:
                    st.write(f"**{name}** — ${spent:.2f} / ${bud:.2f}")
                    st.progress(pct)
                with colB:
                    if bud == 0:
                        st.write("No budget")
                    else:
                        if pct >= 100:
                            st.write("🔴 Over")
                        elif pct >= 90:
                            st.write("🟠 Near")
                        else:
                            st.write("🟢 OK")

            # Transactions table
            st.subheader("Transactions")
            st.dataframe(df_month.sort_values("Date", ascending=False).reset_index(drop=True))

            # Export CSV
            csv_bytes = df_month.to_csv(index=False).encode("utf-8")
            st.download_button("📥 Download Transactions CSV", data=csv_bytes, file_name=f"transactions_{selected_month}.csv", mime="text/csv")

# Tab 3 - Budgets
with tab3:
    st.header("⚙️ Budgets")
    st.write("Set monthly budgets per category. If a category does not exist it will be created.")

    with st.form("budget_form", clear_on_submit=False):
        new_cat = st.text_input("Category name", value="")
        new_budget_amt = st.number_input("Monthly Budget ($)", min_value=0.0, format="%.2f", value=0.0)
        budget_submit = st.form_submit_button("Add / Update Budget")
        if budget_submit:
            if new_cat.strip() == "":
                st.warning("Enter a category name.")
            else:
                update_budget_row(new_cat.strip(), float(new_budget_amt))
                st.success(f"Budget set: {new_cat} → ${new_budget_amt:.2f}")
                load_sheet_dataframe.clear()
                st.experimental_rerun()

    st.write("Existing budgets:")
    if budgets_df.empty:
        st.info("No budgets set yet.")
    else:
        st.table(budgets_df)

# Tab 4 - Goals
with tab4:
    st.header("🎯 Savings Goals")
    st.write("Track savings goals (vacation, emergency fund, etc.)")

    with st.form("goal_form", clear_on_submit=False):
        goal_name = st.text_input("Goal Name")
        target_amt = st.number_input("Target Amount ($)", min_value=0.0, format="%.2f")
        current_amt = st.number_input("Current Saved ($)", min_value=0.0, format="%.2f")
        goal_submit = st.form_submit_button("Add/Update Goal")
        if goal_submit:
            if goal_name.strip() == "":
                st.warning("Please enter a goal name.")
            else:
                update_goal_row(goal_name.strip(), float(target_amt), float(current_amt))
                st.success(f"Saved goal '{goal_name}': ${current_amt:.2f} / ${target_amt:.2f}")
                load_sheet_dataframe.clear()
                st.experimental_rerun()

    if goals_df.empty:
        st.info("No goals yet.")
    else:
        for _, r in goals_df.iterrows():
            name = r["Goal Name"]
            target = float(r["Target Amount"])
            current = float(r["Current Saved"])
            pct = int(min(100, (current/target*100) if target > 0 else 0))
            st.write(f"**{name}** — ${current:.2f} / ${target:.2f}")
            st.progress(pct)