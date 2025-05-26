import streamlit as st
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials
from gspread_dataframe import get_as_dataframe, set_with_dataframe
from datetime import datetime # Make sure datetime is imported
import plotly.express as px # Import Plotly Express

# Set page config
st.set_page_config(page_title="My Expenses Dashboard", layout="wide")

# --- START CREDENTIALS HANDLING ---
scopes = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = None
using_secrets = False # Flag to track if secrets were used
creds_file_path = "my-expenses-dashboard-8f329af8d5d5.json"
sheet_name = "expense_tracker"


# --- START CREDENTIALS HANDLING --- # << This line should be AFTER your pasted code.
scopes = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = None

try:
    # Attempt to load credentials from Streamlit Secrets first
    if "google_credentials" in st.secrets:
        creds = Credentials.from_service_account_info(st.secrets["google_credentials"], scopes=scopes)
        using_secrets = True
except st.errors.StreamlitAPIException as e: 
    st.warning(f"Streamlit secrets API error: {e}. Falling back to local file.")
except Exception as e: # Catch any other unexpected error during secrets processing
    st.warning(f"Unexpected error processing st.secrets: {e}. Falling back to local file.")

# If credentials were not loaded from secrets, try the local file
if not creds:
    try:
        creds = Credentials.from_service_account_file(creds_file_path, scopes=scopes)
    except FileNotFoundError:
        st.error(f"Credentials file '{creds_file_path}' not found, and Streamlit secrets are not configured or missing 'google_credentials'.")
        st.info("Please provide credentials: either configure `google_credentials` in Streamlit Cloud secrets (recommended) or place the JSON file at the project root.")
        st.stop()
    except Exception as e: # Catch other errors during local file loading (e.g., malformed JSON)
        st.error(f"Error loading credentials from local file '{creds_file_path}': {e}")
        st.stop()

# If after all attempts, creds are still None
if not creds:
    st.error("Fatal: Could not load Google Sheets credentials from any source. Application cannot proceed.")
    st.stop()
# --- END CREDENTIALS HANDLING ---

# --- START MAIN APPLICATION LOGIC (GSPREAD, DATA PROCESSING, UI) ---
try:
    gc = gspread.authorize(creds)
    sh = gc.open(sheet_name)

    worksheet = sh.sheet1 
    data = worksheet.get_all_records() 
    
    if not data:
        st.warning("The first worksheet is empty or contains no data.")
        st.stop()

    df = pd.DataFrame(data)

    # --- START DATA PREPARATION ---
    if 'Date' in df.columns:
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    else:
        st.error("Column 'Date' not found in the Google Sheet. Please ensure it exists.")
        st.stop()

    if 'Amount in CHF' in df.columns:
        df['Amount in CHF'] = pd.to_numeric(df['Amount in CHF'], errors='coerce')
    else:
        st.error("Column 'Amount in CHF' not found in the Google Sheet. Please ensure it exists.")
        st.stop()
    
    # Optional: Drop rows where critical conversions failed if you prefer
    # df.dropna(subset=['Date', 'Amount in CHF'], inplace=True)
    # --- END DATA PREPARATION ---

    # --- START SIDEBAR AND DATE FILTER ---
    st.sidebar.header("Filters")
    today = pd.Timestamp('now').normalize()

    def set_ytd_dates_callback():
        st.session_state.start_date_ss = pd.Timestamp(datetime(today.year, 1, 1)).normalize()
        st.session_state.end_date_ss = today

    def set_last_3_months_dates_callback():
        st.session_state.start_date_ss = today - pd.DateOffset(months=3)
        st.session_state.end_date_ss = today

    def set_last_6_months_dates_callback():
        st.session_state.start_date_ss = today - pd.DateOffset(months=6)
        st.session_state.end_date_ss = today

    default_start_for_value = today - pd.DateOffset(months=12)
    default_end_for_value = today

    if df['Date'].dropna().empty:
        st.sidebar.warning("No valid dates found in data. Date pickers will default to last 12 months but allow wider selection.")
        min_date_for_picker = today - pd.DateOffset(years=2)
        max_date_for_picker = today
    else:
        min_date_for_picker = df['Date'].min()
        max_date_for_picker = df['Date'].max()
        if default_start_for_value < min_date_for_picker:
            default_start_for_value = min_date_for_picker
        if default_end_for_value > max_date_for_picker:
            default_end_for_value = max_date_for_picker
        if default_start_for_value > default_end_for_value: # Ensure start is not after end
            default_start_for_value = default_end_for_value

    if 'start_date_ss' not in st.session_state:
        st.session_state.start_date_ss = default_start_for_value
    if 'end_date_ss' not in st.session_state:
        st.session_state.end_date_ss = default_end_for_value

    st.sidebar.date_input("Start date", 
                          min_value=min_date_for_picker, 
                          max_value=max_date_for_picker,
                          key='start_date_ss')
    st.sidebar.date_input("End date", 
                          min_value=st.session_state.start_date_ss, 
                          max_value=max_date_for_picker,
                          key='end_date_ss')

    st.sidebar.markdown("---")
    st.sidebar.subheader("Quick Filters")
    b_col1, b_col2, b_col3 = st.sidebar.columns(3)
    with b_col1:
        st.button("YTD", on_click=set_ytd_dates_callback, use_container_width=True)
    with b_col2:
        st.button("Last 3 Months", on_click=set_last_3_months_dates_callback, use_container_width=True)
    with b_col3:
        st.button("Last 6 Months", on_click=set_last_6_months_dates_callback, use_container_width=True)
    st.sidebar.markdown("---")
    
    selected_start_date = pd.to_datetime(st.session_state.start_date_ss)
    selected_end_date = pd.to_datetime(st.session_state.end_date_ss)
    # --- END SIDEBAR AND DATE FILTER ---

    # --- START DATE FILTERING ---
    if pd.isna(selected_start_date) or pd.isna(selected_end_date):
        st.warning("Invalid date range selected. Displaying all data.")
        df_filtered = df.copy() 
    else:
        df_filtered = df[(df['Date'] >= selected_start_date) & (df['Date'] <= selected_end_date)].copy()
    # --- END DATE FILTERING ---

    # --- PRE-CALCULATE MONTHLY AGGREGATED DATA (for Line Chart & Summary Table) ---
    summary_table_final = pd.DataFrame() 
    if not df_filtered.empty:
        df_summary_calc = df_filtered.copy()
        df_summary_calc['Date'] = pd.to_datetime(df_summary_calc['Date'], errors='coerce')
        df_summary_calc['Amount in CHF'] = pd.to_numeric(df_summary_calc['Amount in CHF'], errors='coerce').fillna(0.0)
        df_summary_calc.dropna(subset=['Date'], inplace=True)

        if not df_summary_calc.empty:
            df_summary_calc['Year-Month'] = df_summary_calc['Date'].dt.strftime('%Y-%m')
            monthly_aggregated = df_summary_calc.groupby('Year-Month').agg(
                Income=('Amount in CHF', lambda x: x[x > 0].sum()),
                Expenses=('Amount in CHF', lambda x: x[x < 0].sum())
            ).reset_index()
            monthly_aggregated['Net Income / Loss'] = monthly_aggregated['Income'] + monthly_aggregated['Expenses']
            summary_table_final = monthly_aggregated.sort_values(by='Year-Month', ascending=False) 
    # --- END PRE-CALCULATION OF MONTHLY AGGREGATED DATA ---

    st.title("My Personal Expense Dashboard")

    # --- START KEY METRICS ---
    if df_filtered.empty:
        st.warning("No data available for the selected date range to calculate metrics.")
        total_income = 0.0
        total_expenses = 0.0
        net_income_loss = 0.0
    else:
        df_filtered['Amount in CHF'] = pd.to_numeric(df_filtered['Amount in CHF'], errors='coerce').fillna(0.0)
        total_income = df_filtered[df_filtered['Amount in CHF'] > 0]['Amount in CHF'].sum()
        total_expenses = df_filtered[df_filtered['Amount in CHF'] < 0]['Amount in CHF'].sum()
        net_income_loss = total_income + total_expenses

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(label="Total Income", value=f"CHF {total_income:,.2f}")
    with col2:
        st.metric(label="Total Expenses", value=f"CHF {total_expenses:,.2f}")
    with col3:
        st.metric(label="Net Income / Loss", value=f"CHF {net_income_loss:,.2f}")
    # --- END KEY METRICS --- 

    # --- START VISUALIZATIONS ---
    st.header("Visualizations")
    if df_filtered.empty:
        st.warning("No data available for the selected date range to display charts.")
    else:
        if 'Category' not in df_filtered.columns:
            st.error("Column 'Category' not found. Cannot generate category-based charts.")
        else:
            df_filtered['Amount in CHF'] = pd.to_numeric(df_filtered['Amount in CHF'], errors='coerce').fillna(0.0)
            df_expenses_only_pie = df_filtered[df_filtered['Amount in CHF'] < 0].copy()
            if df_expenses_only_pie.empty:
                st.info("No expense data to display for pie chart.")
            else:
                df_expenses_only_pie['Abs Amount'] = df_expenses_only_pie['Amount in CHF'].abs()
                category_spending_expenses = df_expenses_only_pie.groupby('Category')['Abs Amount'].sum().reset_index()
                category_spending_for_pie_display = category_spending_expenses[category_spending_expenses['Abs Amount'] > 0]
                if not category_spending_for_pie_display.empty:
                    fig_pie = px.pie(category_spending_for_pie_display, 
                                     names='Category', 
                                     values='Abs Amount',
                                     title="Spending by Category")
                    st.plotly_chart(fig_pie, use_container_width=True)
                else:
                    st.info("No category spending data (expenses only) to display for pie chart (or total is zero).")

            if 'category_spending_expenses' in locals() and not category_spending_expenses.empty:
                top_expense_categories_df = category_spending_expenses.nlargest(7, 'Abs Amount')
                top_expense_categories_for_display = top_expense_categories_df[top_expense_categories_df['Abs Amount'] > 0]
                if not top_expense_categories_for_display.empty:
                    fig_bar_expenses = px.bar(top_expense_categories_for_display, 
                                              x='Category', 
                                              y='Abs Amount',
                                              title="Top 7 Expense Categories", 
                                              color='Category')
                    fig_bar_expenses.update_layout(yaxis_title="Total Expenses (CHF Absolute)")
                    st.plotly_chart(fig_bar_expenses, use_container_width=True)
                else:
                    st.info("No data to display for top expense categories bar chart (or total is zero).")
            elif 'df_expenses_only_pie' in locals() and df_expenses_only_pie.empty: # Check if there were any expenses at all
                st.info("No expense data to determine top categories.")
            else: 
                st.info("No category spending data available for top expense categories bar chart.")

            if not summary_table_final.empty:
                chart_data_source = summary_table_final.sort_values(by='Year-Month', ascending=True)
                df_melted_for_line = chart_data_source.melt(
                    id_vars=['Year-Month'], 
                    value_vars=['Income', 'Expenses', 'Net Income / Loss'], 
                    var_name='Metric', 
                    value_name='Amount (CHF)'
                )
                if not df_melted_for_line.empty:
                    fig_financial_summary_line = px.line(
                        df_melted_for_line,
                        x='Year-Month',
                        y='Amount (CHF)',
                        color='Metric',
                        title="Monthly Financial Summary",
                        markers=True
                    )
                    fig_financial_summary_line.update_layout(yaxis_title="Amount (CHF)")
                    st.plotly_chart(fig_financial_summary_line, use_container_width=True)
                else: 
                    st.info("No data available to display monthly financial summary line chart after melting.")
            elif df_filtered.empty: 
                st.info("No data available for the selected date range to generate the monthly financial summary chart.")
            else: 
                st.info("Monthly summary data is not available for the line chart (e.g. no valid date entries).")
    # --- END VISUALIZATIONS ---

    # --- START MONTHLY TRENDS FOR TOP SPENDING CATEGORIES ---
    st.header("Monthly Trends for Top Spending Categories")
    if df_filtered.empty:
        st.info("No data available in the selected period to generate monthly trends for top spending categories.")
    elif 'Category' not in df_filtered.columns or 'Amount in CHF' not in df_filtered.columns:
        st.warning("Required columns ('Category' or 'Amount in CHF') are missing for this chart.")
    else:
        df_expenses = df_filtered[df_filtered['Amount in CHF'] < 0].copy()
        if df_expenses.empty:
            st.info("No expense data in the selected period for this chart.")
        else:
            df_expenses['Abs Amount'] = df_expenses['Amount in CHF'].abs()
            top_categories_overall_spending = df_expenses.groupby('Category')['Abs Amount'].sum().nlargest(5).index.tolist()
            if not top_categories_overall_spending: # Check if list is empty
                st.info("Not enough category expense data to determine top 5 categories.")
            else:
                df_top_category_expenses = df_expenses[df_expenses['Category'].isin(top_categories_overall_spending)].copy()
                df_top_category_expenses['Date'] = pd.to_datetime(df_top_category_expenses['Date'], errors='coerce')
                df_top_category_expenses.dropna(subset=['Date'], inplace=True)
                if df_top_category_expenses.empty:
                    st.info("No valid date entries for top category expenses after filtering.")
                else:
                    df_top_category_expenses['Year-Month'] = df_top_category_expenses['Date'].dt.strftime('%Y-%m')
                    monthly_top_category_trends = df_top_category_expenses.groupby(['Year-Month', 'Category'])['Amount in CHF'].sum().reset_index()
                    monthly_top_category_trends = monthly_top_category_trends.sort_values(by=['Year-Month', 'Category'])
                    if monthly_top_category_trends.empty:
                        st.info("No monthly trend data to display for top categories.")
                    else:
                        fig_top_cat_trends = px.line(
                            monthly_top_category_trends,
                            x='Year-Month',
                            y='Amount in CHF', 
                            color='Category',
                            title="Monthly Expenses: Top 5 Categories",
                            markers=True
                        )
                        fig_top_cat_trends.update_layout(yaxis_title="Total Expenses (CHF)")
                        st.plotly_chart(fig_top_cat_trends, use_container_width=True)
    # --- END MONTHLY TRENDS FOR TOP SPENDING CATEGORIES ---

    # --- START RECENT ACTIVITY: SPENDING IN LAST 10 DAYS ---
    st.header("Recent Activity: Spending in Last 10 Days")
    today_for_recent = pd.Timestamp('now').normalize()
    ten_days_ago = today_for_recent - pd.DateOffset(days=9) 

    df_recent_orig = df.copy() # Use original df for this section
    df_recent_orig['Date'] = pd.to_datetime(df_recent_orig['Date'], errors='coerce')
    df_recent_orig['Amount in CHF'] = pd.to_numeric(df_recent_orig['Amount in CHF'], errors='coerce').fillna(0.0)
    df_recent_orig.dropna(subset=['Date'], inplace=True)

    recent_expenses = df_recent_orig[
        (df_recent_orig['Date'] >= ten_days_ago) & 
        (df_recent_orig['Date'] <= today_for_recent) & 
        (df_recent_orig['Amount in CHF'] < 0)
    ].copy()

    if recent_expenses.empty:
        st.info("No expense transactions recorded in the last 10 days.")
    else:
        if 'Category' not in recent_expenses.columns:
            st.warning("Column 'Category' is missing, cannot display recent spending by category.")
        else:
            recent_expenses['Abs Amount'] = recent_expenses['Amount in CHF'].abs()
            spending_last_10_days = recent_expenses.groupby('Category')['Abs Amount'].sum().reset_index()
            spending_last_10_days = spending_last_10_days[spending_last_10_days['Abs Amount'] > 0]
            if spending_last_10_days.empty:
                st.info("No category spending to display for the last 10 days.")
            else:
                fig_recent_spending = px.bar(
                    spending_last_10_days,
                    x='Category',
                    y='Abs Amount',
                    title="Spending by Category (Last 10 Days)"
                )
                fig_recent_spending.update_layout(yaxis_title="Total Spending (CHF Absolute)")
                st.plotly_chart(fig_recent_spending, use_container_width=True)
    # --- END RECENT ACTIVITY: SPENDING IN LAST 10 DAYS ---

    # --- START MONTHLY INCOME & LOSS SUMMARY TABLE ---
    st.header("Monthly Income & Loss Summary")
    if summary_table_final.empty:
        if df_filtered.empty:
            st.info("No data available to display monthly summary for the selected date range.")
        else: 
            st.info("No valid data to generate monthly summary (e.g., all dates invalid after filtering, or no transactions).")
    else:
        st.dataframe(summary_table_final.style.format({
            'Income': 'CHF {:,.2f}',
            'Expenses': 'CHF {:,.2f}',
            'Net Income / Loss': 'CHF {:,.2f}'
        }), use_container_width=True)
    # --- END MONTHLY INCOME & LOSS SUMMARY TABLE ---

    # --- START RAW DATA EXPANDER ---
    with st.expander("Show Raw Data", expanded=False):
        st.dataframe(df_filtered) 
    # --- END RAW DATA EXPANDER ---

# --- EXCEPTION HANDLING FOR THE MAIN APPLICATION LOGIC ---
except gspread.exceptions.SpreadsheetNotFound:
    st.error(f"Spreadsheet named '{sheet_name}' not found. Please check the name and ensure the service account has access.")
    st.stop()
except gspread.exceptions.APIError as e:
    err_detail = "Unknown error"
    try:
        err_detail = e.response.json().get('error', {}).get('message', str(e))
    except Exception: # In case response is not JSON or structure is unexpected
        err_detail = str(e)
        
    if using_secrets:
        st.error(f"Google Sheets API error using st.secrets: {err_detail}")
    else:
        st.error(f"Google Sheets API error using local file '{creds_file_path}': {err_detail}")
    st.info("Ensure the service account has permissions for Google Sheets and the Drive API, and that the Google Sheets API is enabled in your Google Cloud project.")
    st.stop()
except Exception as e: # General catch-all for other errors within the main app logic
    st.error(f"An unexpected error occurred during data processing or UI rendering: {e}")
    st.exception(e) # Provides full traceback in the Streamlit app for debugging
    st.stop()
# --- END MAIN APPLICATION LOGIC ---
