from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from dotenv import load_dotenv
import os
import pandas as pd
import httpx
from datetime import datetime, timedelta
from urllib.parse import quote

# Force load .env from the project root BEFORE importing services
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(current_dir, "..")
env_path = os.path.join(project_root, ".env")

print(f"Loading .env from: {env_path}")
load_dotenv(env_path, override=True)

from models import ChatRequest, ChatResponse, StoreInfo, ProductInfo
from services.sheet_service import load_stores_data
from services.geo_service import find_nearest_stores
from services.ai_service import get_ai_response, extract_search_intent, configure_genai

from fastapi.staticfiles import StaticFiles

# ... (imports remain)

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variable to store loaded store data
stores_dataframe: pd.DataFrame = pd.DataFrame()
products_dataframe: pd.DataFrame = pd.DataFrame() # Add this line
unique_categories: list[str] = []

# Zalo OAuth Configuration
ZALO_APP_ID = os.environ.get("ZALO_APP_ID", "")
ZALO_APP_SECRET = os.environ.get("ZALO_APP_SECRET", "")
ZALO_REDIRECT_URI = "http://127.0.0.1:8000/auth/zalo/callback"
# Google Sheets Configuration
SHEET_URL = os.getenv("GOOGLE_SHEET_URL", "https://docs.google.com/spreadsheets/d/1ekdjU2lJK1MnBzwFr3B8ws2E8GnK1omLJNbIU8puXPI/edit?gid=815593620#gid=815593620")
SPREADSHEET_ID = "1ekdjU2lJK1MnBzwFr3B8ws2E8GnK1omLJNbIU8puXPI"
GID = "815593620"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid={GID}"

# In-memory session storage (use Redis in production)
sessions = {}

@app.on_event("startup")
async def startup_event():
    global stores_dataframe, unique_categories, products_dataframe
    print("Loading store data on startup...")
    stores_dataframe, products_dataframe = load_stores_data()
    
    if not stores_dataframe.empty and 'category' in stores_dataframe.columns:
        unique_categories = stores_dataframe['category'].dropna().unique().tolist()
        print(f"Loaded {len(stores_dataframe)} stores.")
        print(f"Unique Categories found: {unique_categories}")
    else:
        print("Warning: No categories found in data.")

    print("Configuring Gemini API...")
    configure_genai()


@app.post("/chat", response_model=ChatResponse)
async def chat_with_ai(request: ChatRequest):
    user_message = request.message
    user_latitude = request.latitude
    user_longitude = request.longitude

    if stores_dataframe.empty:
        raise HTTPException(status_code=500, detail="Store data not loaded.")

    # 1. Extract Search Intent (passing dynamic categories)
    search_intent = await extract_search_intent(user_message, unique_categories)
    print(f"User Intent: {search_intent}")

    # 2. Filter Stores (if intent found)
    filtered_stores = pd.DataFrame()
    match_type = None
    is_location_request = search_intent.get('is_location_request') if search_intent else False
    
    if search_intent and not is_location_request:
        # Step 1: Filter by Category (Strict Filter)
        # If intent has a category, we ONLY look at stores in that category.
        if search_intent.get('category'):
            category_term = search_intent['category']
            mask = stores_dataframe['category'].str.contains(category_term, case=False, na=False)
            filtered_stores = stores_dataframe[mask]
            print(f"DEBUG: Filtered down to {len(filtered_stores)} stores in CATEGORY '{category_term}'")
        else:
            # If no category in intent, start with all stores
            filtered_stores = stores_dataframe.copy()

        # Step 2: Filter by Product Name (within the category-filtered list)
        if search_intent.get('product') and not filtered_stores.empty:
            product_term = search_intent['product']
            search_terms = product_term.split()
            mask = pd.Series([True] * len(filtered_stores))
            # Reset index to align with mask
            filtered_stores = filtered_stores.reset_index(drop=True)
            
            for term in search_terms:
                term_mask = (
                    filtered_stores['product_info'].str.contains(term, case=False, na=False) |
                    filtered_stores['store_name'].str.contains(term, case=False, na=False)
                )
                mask = mask & term_mask
            
            product_filtered = filtered_stores[mask]
            
            if not product_filtered.empty:
                filtered_stores = product_filtered
                match_type = 'product'
                print(f"DEBUG: Found {len(filtered_stores)} stores matching PRODUCT '{product_term}'")
            else:
                # Fallback Step 2.5: Try filtering by 'generic_term' if available
                # This helps distinguish "Phone" vs "Laptop" within "Tech" category
                generic_term = search_intent.get('generic_term')
                if generic_term:
                    print(f"DEBUG: Product '{product_term}' not found. Trying generic term '{generic_term}'...")
                    mask = (
                        filtered_stores['product_info'].str.contains(generic_term, case=False, na=False) |
                        filtered_stores['store_name'].str.contains(generic_term, case=False, na=False)
                    )
                    generic_filtered = filtered_stores[mask]
                    
                    if not generic_filtered.empty:
                        filtered_stores = generic_filtered
                        match_type = 'category' # Treat as category match for AI tone
                        print(f"DEBUG: Found {len(filtered_stores)} stores matching GENERIC TERM '{generic_term}'")
                    else:
                        match_type = 'category'
                        print(f"DEBUG: Generic term '{generic_term}' also not found. Falling back to full CATEGORY '{search_intent.get('category')}'")
                else:
                    match_type = 'category'
                    print(f"DEBUG: Product '{product_term}' not found. Falling back to {len(filtered_stores)} stores in CATEGORY '{search_intent.get('category')}'")
        
        elif not filtered_stores.empty:
             # Only Category matched (no product in intent)
             match_type = 'category'

        if filtered_stores.empty:
            print(f"No stores found matching intent '{search_intent}'.")
    else:
        if is_location_request:
            print("User requested location check.")
        else:
            print("No search intent detected. Skipping store lookup.")

    # 3. Find Nearest Stores
    # If it's a location request, we might NOT want to show stores? 
    # Or maybe we still show them if filtered_stores is not empty?
    # If is_location_request is True, filtered_stores is empty (initialized above).
    nearest_stores_data = find_nearest_stores(user_latitude, user_longitude, filtered_stores)

    nearest_stores_response = []
    if nearest_stores_data:
        for store in nearest_stores_data:
            # Find matching products for this store
            store_id = store.get('store_id') # Ensure aggregation keeps store_id, or match by name/lat/lng
            
            # Need to get store_id from aggregation. Let's assume store['store_id'] exists.
            # Filter products_dataframe for this store
            store_products_df = pd.DataFrame()
            if not products_dataframe.empty and 'ID Shop' in products_dataframe.columns:
                 # Ensure types match. ID Shop might be int or str.
                 # Convert store_id to str for comparison if needed
                 import numpy as np
                 # Assuming products_dataframe loaded successfully
                 store_products_df = products_dataframe[products_dataframe['ID Shop'].astype(str) == str(store_id)]
            
            # Filter relevant products based on query if possible
            matching_products = []
            
            if not store_products_df.empty:
                # If product match, prioritize those
                if match_type == 'product' and search_intent.get('product'):
                    terms = search_intent['product'].split()
                    mask = pd.Series([True] * len(store_products_df))
                    for term in terms:
                         mask = mask & (
                             store_products_df['Product Name'].str.contains(term, case=False, na=False) |
                             store_products_df['Tên sản phẩm'].str.contains(term, case=False, na=False)
                         )
                    matched_df = store_products_df[mask]
                    if not matched_df.empty:
                        store_products_df = matched_df

                # Take top 5
                for _, row in store_products_df.head(5).iterrows():
                    # Handle different column names if they vary
                    p_name = row.get('Tên sản phẩm', row.get('Product Name', 'Sản phẩm'))
                    p_price = row.get('Giá bán', row.get('Price', 'Liên hệ'))
                    p_image = row.get('Link ảnh', row.get('Image', ''))
                    p_link = row.get('Link sản phẩm', '')

                    # Clean data
                    if pd.isna(p_price): p_price = "Liên hệ"
                    if pd.isna(p_image): p_image = ""
                    
                    matching_products.append(ProductInfo(
                        name=str(p_name),
                        price=str(p_price),
                        image_url=str(p_image),
                        link=str(p_link)
                    ))

            nearest_stores_response.append(StoreInfo(
                name=store['store_name'],
                address=store['address'],
                lat=store['latitude'],
                lng=store['longitude'],
                distance_km=store['distance_km'],
                zalo_group_link=store.get('zalo_group_link'),
                products=matching_products
            ))

    # 4. Generate AI Response
    ai_reply = await get_ai_response(user_message, nearest_stores_data, search_intent, match_type)

    return ChatResponse(
        reply=ai_reply, 
        nearest_stores=nearest_stores_response,
        trigger_location=is_location_request # Auto-trigger if user asked for location
    )

# ===== Zalo OAuth Routes =====
@app.get("/auth/zalo/callback")
async def zalo_callback(code: str = None, state: str = None, error: str = None, code_verifier: str = None):
    """Zalo OAuth callback endpoint - supports OAuth V4 with PKCE"""
    
    if error:
        return HTMLResponse(content=f"""
            <html><body>
                <h1>Đăng nhập thất bại</h1>
                <p>Lỗi: {error}</p>
                <a href="/login.html">Thử lại</a>
            </body></html>
        """, status_code=400)
    
    if not code:
        return HTMLResponse(content="""
            <html><body>
                <h1>Thiếu mã xác thực</h1>
                <a href="/login.html">Quay lại</a>
            </body></html>
        """, status_code=400)
    
    try:
        # Exchange code for access token
        async with httpx.AsyncClient() as client:
            # Prepare token request data
            token_data_payload = {
                "app_id": ZALO_APP_ID,
                "code": code,
                "grant_type": "authorization_code"
            }
            
            # Add code_verifier if provided (OAuth V4 PKCE)
            if code_verifier:
                token_data_payload["code_verifier"] = code_verifier
            
            token_response = await client.post(
                "https://oauth.zaloapp.com/v4/access_token",
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "secret_key": ZALO_APP_SECRET
                },
                data=token_data_payload
            )
            
            token_data = token_response.json()
            
            if "access_token" not in token_data:
                error_msg = token_data.get("error_description", token_data.get("error", "Không lấy được access token"))
                raise HTTPException(status_code=400, detail=f"Không lấy được access token: {error_msg}")
            
            access_token = token_data["access_token"]
            
            # Get user info
            user_response = await client.get(
                "https://graph.zalo.me/v2.0/me",
                params={"access_token": access_token, "fields": "id,name,picture"}
            )
            
            user_data = user_response.json()
            
            if "id" not in user_data:
                error_msg = user_data.get("error", {}).get("message", "Không lấy được thông tin user")
                raise HTTPException(status_code=400, detail=f"Không lấy được thông tin user: {error_msg}")
            
            # Create session
            session_id = f"zalo_{user_data['id']}_{datetime.now().timestamp()}"
            sessions[session_id] = {
                "user_id": user_data["id"],
                "name": user_data.get("name", "User"),
                "picture": user_data.get("picture", {}).get("data", {}).get("url", ""),
                "login_time": datetime.now().isoformat(),
                "type": "zalo"
            }
            
            # Redirect to frontend with session info
            frontend_url = "http://127.0.0.1:8000/index.html"
            encoded_name = quote(user_data.get("name", "User"))
            user_picture_url = user_data.get("picture", {}).get("data", {}).get("url", "")
            encoded_picture = quote(user_picture_url) if user_picture_url else ""
            
            redirect_url = f"{frontend_url}?session_id={session_id}&user_type=zalo&user_name={encoded_name}&user_picture={encoded_picture}&login_time={datetime.now().isoformat()}"
            
            return HTMLResponse(content=f"""
                <html><body>
                    <h2 style="text-align: center; font-family: Arial; margin-top: 100px;">
                        Đăng nhập thành công! Đang chuyển hướng...
                    </h2>
                    <script>
                        window.location.href = '{redirect_url}';
                    </script>
                </body></html>
            """)
            
    except Exception as e:
        return HTMLResponse(content=f"""
            <html><body>
                <h1>Lỗi xử lý đăng nhập</h1>
                <p>{str(e)}</p>
                <a href="/login.html">Thử lại</a>
            </body></html>
        """, status_code=500)

@app.get("/auth/verify")
async def verify_session(session_id: str = None):
    """Verify user session"""
    if not session_id or session_id not in sessions:
        return {"valid": False}
    
    session = sessions[session_id]
    login_time = datetime.fromisoformat(session["login_time"])
    
    # Check if session expired (24 hours)
    if datetime.now() - login_time > timedelta(hours=24):
        del sessions[session_id]
        return {"valid": False}
    
    return {
        "valid": True,
        "user": {
            "name": session["name"],
            "type": session["type"]
        }
    }


# Mount static files to serve frontend
# We serve the parent directory (project root) where index.html is located
# Place this AFTER all API routes to avoid shadowing
static_dir = os.path.join(os.path.dirname(__file__), "..")
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
