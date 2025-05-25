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

    The application can use credentials from a local JSON file or from Streamlit Community Cloud's secrets management.

    ### 5a. Configuring for Local Development (using JSON file)
    *   You should have a JSON credentials file for a Google Service Account.
    *   Rename this file to `my-expenses-dashboard-8f329af8d5d5.json` and place it in the root directory of this project (the same directory as `app.py`).
    *   **Important:** Ensure this service account has permission to access the Google Sheet you want to display. You'll need to share the Google Sheet with the service account's email address (found in the JSON credentials file, usually under `client_email`).

    ### 5b. Configuring for Streamlit Community Cloud (using `st.secrets`)

    When deploying to Streamlit Community Cloud, it's best to use Streamlit's built-in secrets management for your Google Service Account credentials instead of uploading the JSON file.

    1.  **Prepare your credentials**: You need the content of your service account JSON file.
    2.  **Access Secrets Management**: In your app's page on Streamlit Community Cloud, go to "Settings" > "Secrets".
    3.  **Add the secret**: Create a new secret with the key `google_credentials`. The value should be the entire content of your JSON service account key file, formatted as a TOML dictionary.

        **Example TOML structure for `st.secrets`:**
        ```toml
        [google_credentials]
        type = "service_account"
        project_id = "your-project-id"
        private_key_id = "your-private-key-id"
        private_key = "-----BEGIN PRIVATE KEY-----\nYOUR_PRIVATE_KEY_HERE\n-----END PRIVATE KEY-----\n" # Ensure newlines are escaped as \n
        client_email = "your-service-account-email@your-project-id.iam.gserviceaccount.com"
        client_id = "your-client-id"
        auth_uri = "https://accounts.google.com/o/oauth2/auth"
        token_uri = "https://oauth2.googleapis.com/token"
        auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
        client_x509_cert_url = "your-service-account-client-x509-cert-url.com"
        universe_domain = "googleapis.com" # Or your specific universe domain if applicable
        ```
        **Important on `private_key`**: The `private_key` value in your TOML secrets must have its newline characters (`\n`) escaped as `\\n` if you are pasting it directly. Alternatively, you can often paste it as a multi-line basic string in TOML if your secrets editor supports it well, but escaping `\n` is safer. The application expects the standard format from the JSON key.

        The `app.py` script is configured to automatically use these secrets if they are present. If running locally, it will fall back to using the `my-expenses-dashboard-8f329af8d5d5.json` file.

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
