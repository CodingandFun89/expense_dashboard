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
scopes = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = None
using_secrets = False # Flag to track if secrets were used
# Define creds_file path at a higher scope
creds_file_path = "my-expenses-dashboard-8f329af8d5d5.json"
sheet_name = "expense_tracker" # Define sheet_name here or ensure it's globally available

try:
    # Attempt to load credentials from Streamlit Secrets first
    if "google_credentials" in st.secrets and isinstance(st.secrets["google_credentials"], dict):
        # st.write("Attempting to use credentials from st.secrets") # Optional debug
        creds = Credentials.from_service_account_info(st.secrets["google_credentials"], scopes=scopes)
        using_secrets = True
        # st.write("Successfully used credentials from st.secrets") # Optional debug
    # No specific error for "google_credentials" key not being a dict, covered by 'if not creds' later
except st.errors.StreamlitAPIException as e: 
    # Catch errors specifically from st.secrets access if it's not just a missing key but API issue
    st.warning(f"Streamlit secrets API error: {e}. Falling back to local file.")
except Exception as e: # Catch any other unexpected error during secrets processing
    st.warning(f"Unexpected error processing st.secrets: {e}. Falling back to local file.")


# If credentials were not loaded from secrets, try the local file
if not creds:
    # st.write(f"Attempting to use credentials from local file: {creds_file_path}") # Optional debug
    try:
        creds = Credentials.from_service_account_file(creds_file_path, scopes=scopes)
        # st.write("Successfully used credentials from local file") # Optional debug
    except FileNotFoundError:
        st.error(f"Credentials file '{creds_file_path}' not found, and Streamlit secrets are not configured or missing 'google_credentials'.")
        st.info("Please provide credentials: either configure `google_credentials` in Streamlit Cloud secrets (recommended) or place the JSON file at the project root.")
        st.stop()
    except Exception as e: # Catch other errors during local file loading (e.g., malformed JSON)
        st.error(f"Error loading credentials from local file '{creds_file_path}': {e}")
        st.stop()

# If after all attempts, creds are still None (should ideally be caught by specific errors above)
if not creds:
    st.error("Fatal: Could not load Google Sheets credentials from any source. Application cannot proceed.")
    st.stop()

# Authorize gspread and open sheet (this part can be in its own try-except for gspread specific errors)
try:
    gc = gspread.authorize(creds)
    sh = gc.open(sheet_name) # Use the defined sheet_name

    # Read data from the first worksheet (moved from the outer try-except)
    worksheet = sh.sheet1 
    data = worksheet.get_all_records() 
    
    if not data:
        st.warning("The first worksheet is empty or contains no data.")
        st.stop()

    df = pd.DataFrame(data)

    # --- START DATA PREPARATION --- (This remains part of the main application flow after successful data loading)
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

        today = pd.Timestamp('now').normalize()

        # --- Callback functions for Quick Filters ---
        # Ensure 'today' is defined before these functions are.
        def set_ytd_dates_callback():
            st.session_state.start_date_ss = pd.Timestamp(datetime(today.year, 1, 1)).normalize()
            st.session_state.end_date_ss = today

        def set_last_3_months_dates_callback():
            st.session_state.start_date_ss = today - pd.DateOffset(months=3)
            st.session_state.end_date_ss = today

        def set_last_6_months_dates_callback():
            st.session_state.start_date_ss = today - pd.DateOffset(months=6)
            st.session_state.end_date_ss = today
        # --- End Callback functions ---

        # Default desired range: last 12 months
        default_start_for_value = today - pd.DateOffset(months=12)
        default_end_for_value = today

        # Determine overall min/max bounds for the date pickers based on data
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
            if default_start_for_value > default_end_for_value:
                default_start_for_value = default_end_for_value

        # Initialize session state for dates if they don't exist
        if 'start_date_ss' not in st.session_state:
            st.session_state.start_date_ss = default_start_for_value
        if 'end_date_ss' not in st.session_state:
            st.session_state.end_date_ss = default_end_for_value

        # Date inputs linked to session state
        st.sidebar.date_input("Start date", 
                              value=st.session_state.start_date_ss, 
                              min_value=min_date_for_picker, 
                              max_value=max_date_for_picker,
                              key='start_date_ss')
        st.sidebar.date_input("End date", 
                              value=st.session_state.end_date_ss, 
                              min_value=st.session_state.start_date_ss, 
                              max_value=max_date_for_picker,
                              key='end_date_ss')

        # Quick Filter Buttons
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
        
        # Convert selected dates from session state to Timestamp for filtering
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
        summary_table_final = pd.DataFrame() # Initialize as empty
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
                # This is sorted descending for the table, will re-sort for chart
                summary_table_final = monthly_aggregated.sort_values(by='Year-Month', ascending=False) 
        # --- END PRE-CALCULATION OF MONTHLY AGGREGATED DATA ---

        # Main dashboard title
        st.title("My Personal Expense Dashboard")

        # --- START KEY METRICS ---
        if df_filtered.empty:
            st.warning("No data available for the selected date range to calculate metrics.")
            total_income = 0.0
            total_expenses = 0.0 # Sum of negative numbers, so 0.0 is a neutral starting point
            net_income_loss = 0.0
            # num_transactions = 0 # Removed
        else:
            # Ensure 'Amount in CHF' is numeric
            df_filtered['Amount in CHF'] = pd.to_numeric(df_filtered['Amount in CHF'], errors='coerce').fillna(0.0)
            
            total_income = df_filtered[df_filtered['Amount in CHF'] > 0]['Amount in CHF'].sum()
            total_expenses = df_filtered[df_filtered['Amount in CHF'] < 0]['Amount in CHF'].sum() # Will be negative or zero
            net_income_loss = total_income + total_expenses
            # num_transactions = len(df_filtered) # Removed

        # --- Update st.metric display ---
        col1, col2, col3 = st.columns(3) # Changed to 3 columns

        with col1:
            st.metric(label="Total Income", value=f"CHF {total_income:,.2f}")
        with col2:
            st.metric(label="Total Expenses", value=f"CHF {total_expenses:,.2f}") # This will show a negative number
        with col3:
            st.metric(label="Net Income / Loss", value=f"CHF {net_income_loss:,.2f}")
        # col4 and its st.metric for Number of Transactions removed
        # --- END Update st.metric display ---
        # --- END KEY METRICS --- 

        # --- START VISUALIZATIONS ---
        st.header("Visualizations")

        if df_filtered.empty:
            st.warning("No data available for the selected date range to display charts.")
        else:
            # Ensure 'Category' column exists for category-based charts
            if 'Category' not in df_filtered.columns:
                st.error("Column 'Category' not found. Cannot generate category-based charts.")
            else:
                # --- Update for Pie Chart: Spending by Category (Expenses Only) ---
                # Ensure 'Amount in CHF' is numeric (already done in data prep, but good for isolated logic block)
                df_filtered['Amount in CHF'] = pd.to_numeric(df_filtered['Amount in CHF'], errors='coerce').fillna(0.0)

                df_expenses_only_pie = df_filtered[df_filtered['Amount in CHF'] < 0].copy()
                if df_expenses_only_pie.empty:
                    st.info("No expense data to display for pie chart.")
                else:
                    df_expenses_only_pie['Abs Amount'] = df_expenses_only_pie['Amount in CHF'].abs()
                    category_spending_expenses = df_expenses_only_pie.groupby('Category')['Abs Amount'].sum().reset_index()
                    
                    # Filter out categories with zero sum for pie chart
                    category_spending_for_pie_display = category_spending_expenses[category_spending_expenses['Abs Amount'] > 0]

                    if not category_spending_for_pie_display.empty:
                        fig_pie = px.pie(category_spending_for_pie_display, 
                                         names='Category', 
                                         values='Abs Amount',  # Use the column with absolute sums
                                         title="Spending by Category")
                        st.plotly_chart(fig_pie, use_container_width=True)
                    else:
                        st.info("No category spending data (expenses only) to display for pie chart (or total is zero).")
                # --- End Update for Pie Chart ---

                # --- Update for Bar Chart: Top 5 Expense Categories ---
                # Reusing category_spending_expenses from the Pie Chart logic which is:
                # df_expenses_only_pie.groupby('Category')['Abs Amount'].sum().reset_index()
                if 'category_spending_expenses' in locals() and not category_spending_expenses.empty:
                    top_expense_categories_df = category_spending_expenses.nlargest(7, 'Abs Amount') # Changed to 7
                    # Filter out categories with zero sum for bar chart display (already done by Abs Amount > 0 in pie chart's source)
                    # but good to ensure if logic changes:
                    top_expense_categories_for_display = top_expense_categories_df[top_expense_categories_df['Abs Amount'] > 0]

                    if not top_expense_categories_for_display.empty:
                         fig_bar_expenses = px.bar(top_expense_categories_for_display, 
                                                 x='Category', 
                                                 y='Abs Amount', # Use the column with absolute sums of expenses
                                                 title="Top 7 Expense Categories", # New title
                                                 color='Category')
                         fig_bar_expenses.update_layout(yaxis_title="Total Expenses (CHF Absolute)")
                         st.plotly_chart(fig_bar_expenses, use_container_width=True)
                    else:
                        # This case would mean that even top 5 categories have 0 or less expense,
                        # or category_spending_expenses was empty after all.
                        st.info("No data to display for top expense categories bar chart (or total is zero).")
                # Check if there were any expenses at all, if category_spending_expenses wasn't defined or was empty
                # This relies on df_expenses_only_pie being defined in the pie chart section.
                elif 'df_expenses_only_pie' in locals() and df_expenses_only_pie.empty:
                     st.info("No expense data to determine top categories (previously checked for pie chart).")
                else: # Fallback if category_spending_expenses wasn't found or other conditions
                     st.info("No category spending data available for top expense categories bar chart.")
                # --- End Update for Bar Chart ---


            # --- START Updated Line Chart: Monthly Financial Summary ---
            if not summary_table_final.empty:
                chart_data_source = summary_table_final.sort_values(by='Year-Month', ascending=True) # Ensure chronological order

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
                else: # Should not happen if summary_table_final was not empty
                    st.info("No data available to display monthly financial summary line chart after melting.")
            elif df_filtered.empty: # This covers the case where df_filtered was empty initially
                st.info("No data available for the selected date range to generate the monthly financial summary chart.")
            else: # This covers if df_filtered was not empty, but summary_table_final became empty (e.g., all dates invalid)
                 st.info("Monthly summary data is not available for the line chart (e.g. no valid date entries).")
            # --- END Updated Line Chart: Monthly Financial Summary ---
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

                if len(top_categories_overall_spending) == 0:
                    st.info("Not enough category expense data to determine top 5 categories.")
                else:
                    df_top_category_expenses = df_expenses[df_expenses['Category'].isin(top_categories_overall_spending)].copy() # Use .copy()
                    
                    # Ensure 'Date' column is datetime and handle NaT
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
                                y='Amount in CHF', # These are the negative sums
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
        ten_days_ago = today_for_recent - pd.DateOffset(days=9) # Inclusive of today

        # Use a copy of the original df for this section to avoid conflicts with df_filtered
        df_recent = df.copy() 
        # Ensure correct data types - this should ideally be handled at initial df load,
        # but re-applying here makes this section self-contained and robust.
        df_recent['Date'] = pd.to_datetime(df_recent['Date'], errors='coerce')
        df_recent['Amount in CHF'] = pd.to_numeric(df_recent['Amount in CHF'], errors='coerce').fillna(0.0)
        df_recent.dropna(subset=['Date'], inplace=True) # Remove rows where date conversion failed

        recent_expenses = df_recent[
            (df_recent['Date'] >= ten_days_ago) & 
            (df_recent['Date'] <= today_for_recent) & 
            (df_recent['Amount in CHF'] < 0)
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

        # --- START MONTHLY INCOME & LOSS SUMMARY ---
        st.header("Monthly Income & Loss Summary")

        # Use the pre-calculated summary_table_final
        if summary_table_final.empty:
            if df_filtered.empty: # This condition implies summary_table_final would be empty too
                 st.info("No data available to display monthly summary for the selected date range.")
            else: # This implies df_filtered was not empty, but summary_table_final is (e.g. no valid dates after processing)
                 st.info("No valid data to generate monthly summary (e.g., all dates invalid after filtering, or no transactions).")
        else:
            # summary_table_final is not empty here, and is already sorted descending.
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
# The main application logic continues from here, using 'df'.
# The specific FileNotFoundError and general Exception for the initial credential loading have been handled above.
# Now, handle gspread specific errors for gc.open and worksheet operations.
except gspread.exceptions.SpreadsheetNotFound:
    st.error(f"Spreadsheet named '{sheet_name}' not found. Please check the name and ensure the service account has access.")
    st.stop()
except gspread.exceptions.APIError as e:
    err_detail = e.response.json().get('error', {}).get('message', str(e))
    if using_secrets:
        st.error(f"Google Sheets API error using st.secrets: {err_detail}")
    else:
        st.error(f"Google Sheets API error using local file '{creds_file_path}': {err_detail}")
    st.info("Ensure the service account has permissions for Google Sheets and the Drive API, and that the Google Sheets API is enabled in your Google Cloud project.")
    st.stop()
except Exception as e: # Catch-all for other gspread or sheet processing issues
    st.error(f"An error occurred while accessing Google Sheets: {e}")
    st.stop()

# Ensure the rest of the app's original main try-except structure (if any) is maintained
# For this task, the refactoring focuses on the credential and gspread.authorize/open part.
# The data processing and Streamlit element creation logic (df_filtered, metrics, charts)
# should follow this successfully loaded 'df'.
