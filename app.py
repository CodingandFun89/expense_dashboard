import streamlit as st
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials
from gspread_dataframe import get_as_dataframe, set_with_dataframe
from datetime import datetime # Make sure datetime is imported
import plotly.express as px # Import Plotly Express

# Set page config
st.set_page_config(page_title="My Expenses Dashboard", layout="wide")

# Google Sheets API authentication
try:
    creds_file = "my-expenses-dashboard-8f329af8d5d5.json"
    scopes = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_file(creds_file, scopes=scopes)
    gc = gspread.authorize(creds)

    # Open the Google Sheet
    sheet_name = "expense_tracker"
    try:
        sh = gc.open(sheet_name)
    except gspread.exceptions.SpreadsheetNotFound:
        st.error(f"Spreadsheet named '{sheet_name}' not found. Please check the name and ensure the service account has access.")
        st.stop()

    # Read data from the first worksheet
    try:
        worksheet = sh.sheet1 # Or use sh.worksheet("SheetName") if you know the name
        data = worksheet.get_all_records() # Gets all data as a list of dictionaries
        
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
        
        # Optional: Handle rows with conversion errors if necessary
        # For example, drop rows where critical conversions failed:
        # df.dropna(subset=['Date', 'Amount in CHF'], inplace=True)
        # Or inform the user:
        # if df['Date'].isnull().any() or df['Amount in CHF'].isnull().any():
        #     st.warning("Some rows had errors during data type conversion and might be excluded or result in errors.")
        # --- END DATA PREPARATION ---

        # --- START SIDEBAR AND DATE FILTER ---
        st.sidebar.header("Filters")

        # Ensure df['Date'] has valid datetime objects and is not empty
        if df['Date'].dropna().empty:
            st.sidebar.warning("No valid dates found in data. Using default range (last month).")
            # Default to today or a fixed range if no data
            min_date_for_input = pd.Timestamp('now').normalize() - pd.DateOffset(months=1)
            max_date_for_input = pd.Timestamp('now').normalize()
            selected_start_date_default = min_date_for_input
            selected_end_date_default = max_date_for_input
        else:
            min_date_for_input = df['Date'].min()
            max_date_for_input = df['Date'].max()
            selected_start_date_default = min_date_for_input
            selected_end_date_default = max_date_for_input
            # Ensure defaults are within the actual min/max of the data to avoid errors if sheet is empty then repopulated
            if selected_start_date_default < min_date_for_input:
                 selected_start_date_default = min_date_for_input
            if selected_end_date_default > max_date_for_input:
                selected_end_date_default = max_date_for_input


        selected_start_date = st.sidebar.date_input("Start date", selected_start_date_default, min_value=min_date_for_input, max_value=max_date_for_input)
        selected_end_date = st.sidebar.date_input("End date", selected_end_date_default, min_value=selected_start_date, max_value=max_date_for_input) # min_value for end_date is selected_start_date

        # Convert selected dates to Timestamp for comparison, if they are not already
        selected_start_date = pd.to_datetime(selected_start_date)
        selected_end_date = pd.to_datetime(selected_end_date)
        # --- END SIDEBAR AND DATE FILTER ---

        # --- START DATE FILTERING ---
        if pd.isna(selected_start_date) or pd.isna(selected_end_date):
            st.warning("Invalid date range selected. Displaying all data.")
            df_filtered = df.copy() 
        else:
            df_filtered = df[(df['Date'] >= selected_start_date) & (df['Date'] <= selected_end_date)].copy()
        # --- END DATE FILTERING ---

        # Main dashboard title
        st.title("My Personal Expense Dashboard")

        # --- START KEY METRICS ---
        if df_filtered.empty:
            st.warning("No data available for the selected date range to calculate metrics.")
            total_expenses = 0.0
            num_transactions = 0
            avg_expense = 0.0
        else:
            # Ensure 'Amount in CHF' is numeric
            df_filtered['Amount in CHF'] = pd.to_numeric(df_filtered['Amount in CHF'], errors='coerce').fillna(0.0)
            
            total_income = df_filtered[df_filtered['Amount in CHF'] > 0]['Amount in CHF'].sum()
            total_expenses = df_filtered[df_filtered['Amount in CHF'] < 0]['Amount in CHF'].sum() # Will be negative or zero
            net_income_loss = total_income + total_expenses
            num_transactions = len(df_filtered)

        # --- Update st.metric display ---
        col1, col2, col3, col4 = st.columns(4) # Use 4 columns

        with col1:
            st.metric(label="Total Income", value=f"CHF {total_income:,.2f}")
        with col2:
            st.metric(label="Total Expenses", value=f"CHF {total_expenses:,.2f}") # This will show a negative number
        with col3:
            st.metric(label="Net Income / Loss", value=f"CHF {net_income_loss:,.2f}")
        with col4:
            st.metric(label="Number of Transactions", value=num_transactions)
        # --- END Update st.metric display ---
        # --- END KEY METRICS --- # This comment seems to be part of the old structure, might need to adjust if it causes confusion

        # --- START VISUALIZATIONS ---
        st.header("Visualizations")

        if df_filtered.empty:
            st.warning("No data available for the selected date range to display charts.")
        else:
            # Ensure 'Category' column exists for category-based charts
            if 'Category' not in df_filtered.columns:
                st.error("Column 'Category' not found. Cannot generate category-based charts.")
            else:
                # Pie Chart: Spending by Category
                # Ensure 'Amount in CHF' is numeric for calculations
                df_filtered['Amount in CHF'] = pd.to_numeric(df_filtered['Amount in CHF'], errors='coerce').fillna(0.0)
                
                category_spending = df_filtered.groupby('Category')['Amount in CHF'].apply(lambda x: x.abs().sum()).reset_index()
                # Filter out categories with zero or negative sum for pie chart (abs should make it non-negative, but sum could be zero)
                category_spending_for_pie = category_spending[category_spending['Amount in CHF'] > 0]

                if not category_spending_for_pie.empty:
                    fig_pie = px.pie(category_spending_for_pie, names='Category', values='Amount in CHF', title="Spending by Category")
                    st.plotly_chart(fig_pie, use_container_width=True)
                else:
                    st.info("No category spending data to display for pie chart (or total is zero).")

                # Bar Chart: Top 5 Categories (using category_spending which has absolute sums)
                if not category_spending.empty: # Use the original category_spending which might include zero sums for ranking
                    top_categories = category_spending.nlargest(5, 'Amount in CHF')
                    # Filter out categories with zero or negative sum for bar chart display
                    top_categories_for_bar = top_categories[top_categories['Amount in CHF'] > 0]
                    if not top_categories_for_bar.empty:
                         fig_bar = px.bar(top_categories_for_bar, x='Category', y='Amount in CHF', title="Top 5 Spending Categories", color='Category')
                         fig_bar.update_layout(yaxis_title="Total Spending (CHF Absolute)")
                         st.plotly_chart(fig_bar, use_container_width=True)
                    else:
                        st.info("No data to display for top categories bar chart (or total is zero).")
                # else: # This case is implicitly handled if category_spending is empty due to no categories
                #    st.info("No category data for bar chart.")


            # Line Chart: Spending Over Time
            # Ensure 'Date' and 'Amount in CHF' are suitable
            if 'Date' not in df_filtered.columns:
                st.error("Column 'Date' not found. Cannot generate monthly spending chart.")
            else:
                df_filtered_for_line = df_filtered.copy()
                # Ensure 'Amount in CHF' is numeric for sum (already done if category charts ran, but good for standalone)
                df_filtered_for_line['Amount in CHF'] = pd.to_numeric(df_filtered_for_line['Amount in CHF'], errors='coerce').fillna(0.0)
                df_filtered_for_line['Month'] = df_filtered_for_line['Date'].dt.to_period('M').astype(str) 
                monthly_spending = df_filtered_for_line.groupby('Month')['Amount in CHF'].sum().reset_index()
                monthly_spending = monthly_spending.sort_values('Month') 
                
                if not monthly_spending.empty:
                    fig_line = px.line(monthly_spending, x='Month', y='Amount in CHF', title="Monthly Spending Over Time", markers=True)
                    fig_line.update_layout(xaxis_title="Month", yaxis_title="Total Expenses (CHF)")
                    st.plotly_chart(fig_line, use_container_width=True)
                else:
                    st.info("No monthly spending data to display for line chart.")
        # --- END VISUALIZATIONS ---

        # --- START MONTHLY INCOME & LOSS SUMMARY ---
        st.header("Monthly Income & Loss Summary")

        if df_filtered.empty:
            st.info("No data available to display monthly summary for the selected date range.")
        else:
            df_summary_calc = df_filtered.copy()
            # Ensure 'Date' is datetime and 'Amount in CHF' is numeric
            # These should already be handled by earlier data preparation, but re-applying ensures robustness
            df_summary_calc['Date'] = pd.to_datetime(df_summary_calc['Date'], errors='coerce')
            df_summary_calc['Amount in CHF'] = pd.to_numeric(df_summary_calc['Amount in CHF'], errors='coerce').fillna(0.0)
            
            # Drop rows where Date conversion might have failed, essential for strftime
            df_summary_calc.dropna(subset=['Date'], inplace=True)

            if df_summary_calc.empty: # Check again after potential dropna
                st.info("No valid date entries to generate monthly summary.")
            else:
                df_summary_calc['Year-Month'] = df_summary_calc['Date'].dt.strftime('%Y-%m')
                
                # Group by Year-Month and aggregate
                monthly_aggregated = df_summary_calc.groupby('Year-Month').agg(
                    Income=('Amount in CHF', lambda x: x[x > 0].sum()),
                    Expenses=('Amount in CHF', lambda x: x[x < 0].sum())
                ).reset_index()
                
                monthly_aggregated['Net Income / Loss'] = monthly_aggregated['Income'] + monthly_aggregated['Expenses']
                
                # Sort by Year-Month descending
                summary_table_final = monthly_aggregated.sort_values(by='Year-Month', ascending=False)
                
                if summary_table_final.empty:
                    st.info("No monthly summary data to display.")
                else:
                    st.dataframe(summary_table_final.style.format({
                        'Income': 'CHF {:,.2f}',
                        'Expenses': 'CHF {:,.2f}',
                        'Net Income / Loss': 'CHF {:,.2f}'
                    }), use_container_width=True)
        # --- END MONTHLY INCOME & LOSS SUMMARY ---

        # --- START RAW DATA EXPANDER ---
        with st.expander("Show Raw Data", expanded=False):
            st.dataframe(df_filtered) 
        # --- END RAW DATA EXPANDER ---

    except Exception as e:
        st.error(f"Error reading worksheet or processing data: {e}")
        st.stop()


except FileNotFoundError:
    st.error(f"Credentials file '{creds_file}' not found. Make sure it's in the same directory as app.py.")
    st.info("Please upload your Google Service Account credentials JSON file and name it 'my-expenses-dashboard-8f329af8d5d5.json'.")
    st.stop()
except Exception as e:
    st.error(f"An error occurred during Google Sheets authentication or setup: {e}")
    st.stop()
