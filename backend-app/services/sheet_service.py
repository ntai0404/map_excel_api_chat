import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os

# For simplicity, we'll use a mock CSV file instead of Google Sheets
# In a real scenario, you would set up gspread and authenticate
# scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
# credentials = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
# client = gspread.authorize(credentials)

# Function to load store data from Google Sheet CSV
def clean_coordinate(value):
    """
    Cleans coordinate strings that might have multiple dots (e.g., '105.820.730').
    Assumes the first dot is the decimal separator and removes subsequent dots.
    """
    if pd.isna(value):
        return 0.0
    s = str(value)
    if s.count('.') > 1:
        parts = s.split('.')
        # Keep the first part and the second part as the integer and fractional parts
        # But wait, '105.820.730' -> 105.820730
        # So we join everything after the first part
        return float(parts[0] + '.' + ''.join(parts[1:]))
    try:
        return float(s)
    except ValueError:
        return 0.0

def load_stores_data():
    csv_url = "https://docs.google.com/spreadsheets/d/1FlVCrM1jAKv3GLKhT6B05Vx379xdOCNAj8HDPPLIxvA/export?format=csv&gid=0"
    try:
        df = pd.read_csv(csv_url)
        # Ensure required columns exist
        required_columns = ["store_id", "store_name", "address", "category", "product_info", "promotion", "latitude", "longitude"]
        if not all(col in df.columns for col in required_columns):
            print(f"Error: Missing columns in Google Sheet. Expected: {required_columns}")
            return pd.DataFrame()
        
        # Clean coordinates
        df['latitude'] = df['latitude'].apply(clean_coordinate)
        df['longitude'] = df['longitude'].apply(clean_coordinate)

        print(f"Store data loaded successfully from Google Sheet. {len(df)} records found.")
        return df
    except Exception as e:
        print(f"Error loading data from Google Sheet: {e}")
        return pd.DataFrame()

if __name__ == '__main__':
    # Example usage (for testing purposes)
    store_df = load_stores_data()
    print(store_df.head())
