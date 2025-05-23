import streamlit as st
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials
from gspread_dataframe import get_as_dataframe, set_with_dataframe

# Set page config
st.set_page_config(page_title="My Expenses Dashboard", layout="wide")

# Google Sheets API authentication
try:
    creds_file = "my-expenses-dashboard-8f329af8d5d5.json"
    scopes = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_file(creds_file, scopes=scopes)
    gc = gspread.authorize(creds)

    # Open the Google Sheet
    sheet_name = "Automated_blogging"
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

        # Display the DataFrame
        st.title("My Expenses")
        st.dataframe(df)

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
