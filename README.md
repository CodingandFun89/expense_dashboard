# Streamlit Google Sheets Expense Dashboard

This application displays data from a Google Sheet in a Streamlit web interface.

## Setup Instructions

1.  **Prerequisites:**
    *   Python 3.7+
    *   pip (Python package installer)

2.  **Clone the repository (if applicable) or download the files.**

3.  **Create and activate a virtual environment (recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

4.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

5.  **Add Google Service Account Credentials:**
    *   You should have a JSON credentials file for a Google Service Account.
    *   Rename this file to `my-expenses-dashboard-8f329af8d5d5.json` and place it in the root directory of this project (the same directory as `app.py`).
    *   **Important:** Ensure this service account has permission to access the Google Sheet you want to display. You'll need to share the Google Sheet with the service account's email address (found in the JSON credentials file, usually under `client_email`).

6.  **Ensure your Google Sheet is correctly named:**
    *   The application is configured to open a Google Sheet named "expense_tracker". If your sheet has a different name, you'll need to update it in `app.py` (variable `sheet_name`).

## Running the Application

Once the dependencies are installed and the credentials file is in place:

1.  Open your terminal or command prompt.
2.  Navigate to the project's root directory.
3.  Run the Streamlit application using the following command:
    ```bash
    streamlit run app.py
    ```
4.  Streamlit will typically open the application automatically in your web browser. If not, it will display a local URL (e.g., `http://localhost:8501`) that you can open.

## Troubleshooting

*   **`Credentials file 'my-expenses-dashboard-8f329af8d5d5.json' not found`**: Make sure your credentials JSON file is correctly named and placed in the root project directory.
*   **`Spreadsheet named 'expense_tracker' not found`**:
    *   Verify the sheet name in `app.py` matches your Google Sheet's name.
    *   Ensure the service account (whose email is in your JSON credentials) has been granted at least "Viewer" access to the Google Sheet. Share the sheet with this email address.
*   **Other authentication errors**: Double-check that the Google Sheets API and Google Drive API are enabled for your project in the Google Cloud Console.
