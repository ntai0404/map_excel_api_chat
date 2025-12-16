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
from services.ai_service import get_ai_response, extract_search_intent, configure_genai, smart_product_filter
from geopy.distance import geodesic

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
ZALO_REDIRECT_URI = os.environ.get("ZALO_REDIRECT_URI", "http://127.0.0.1:8000/auth/zalo/callback")
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
    # Unpack 3 values: stores, products, and raw categories
    stores_dataframe, products_dataframe, unique_categories = load_stores_data()
    
    if not stores_dataframe.empty:
        # unique_categories is now list(SHEET_GIDS.values()) directly
        print(f"Loaded {len(stores_dataframe)} stores.")
        print(f"Unique Categories found (Direct from Sheets): {unique_categories}")
    else:
        print("Warning: No categories found in data.")

    print("Configuring Gemini API...")
    configure_genai()


def regex_search_all_products(query: str, limit: int = 3) -> pd.DataFrame:
    """
    Search across all products using regex
    
    Args:
        query: Search query
        limit: Max results to return
    
    Returns:
        DataFrame of matched products
    """
    if products_dataframe.empty:
        return pd.DataFrame()
    
    search_terms = query.split()
    mask = pd.Series([True] * len(products_dataframe))
    
    for term in search_terms:
        term_mask = products_dataframe['Tên sản phẩm'].str.contains(
            term, case=False, na=False
        )
        mask = mask & term_mask
    
    return products_dataframe[mask].head(limit)



@app.post("/chat", response_model=ChatResponse)
async def chat_with_ai(request: ChatRequest):
    user_message = request.message
    user_latitude = request.latitude
    user_longitude = request.longitude

    if stores_dataframe.empty:
        raise HTTPException(status_code=500, detail="Store data not loaded.")

    # STEP 1: AI Call #1 - Extract Search Intent
    search_intent = await extract_search_intent(user_message, unique_categories)
    print(f"User Intent: {search_intent}")
    
    is_location_request = search_intent.get('is_location_request') if search_intent else False
    is_general_inquiry = search_intent.get('is_general_inquiry') if search_intent else False
    
    # Handle general inquiries (e.g., "bạn bán những gì", "xin chào")
    if is_general_inquiry:
        print("User asked general inquiry about products.")
        
        # Check if it's a greeting
        greeting_keywords = ["xin chào", "chào", "hello", "hi", "hey"]
        is_greeting = any(k in user_message.lower() for k in greeting_keywords)
        
        if is_greeting:
            category_list = ", ".join(unique_categories[:10])
            reply = f"Xin chào! Chúc bạn một ngày tốt lành! 😊 Shop em có rất nhiều ngành hàng như: {category_list}... và còn nhiều sản phẩm khác nữa ạ! Bạn muốn tìm sản phẩm gì hôm nay ạ?"
        else:
            category_list = ", ".join(unique_categories[:10])
            reply = f"Dạ shop em có rất nhiều ngành hàng như: {category_list}... và còn nhiều sản phẩm khác nữa ạ! Anh/chị muốn tìm sản phẩm gì cụ thể không ạ?"
        
        return ChatResponse(
            reply=reply,
            nearest_stores=[]
        )
    
    # Handle location requests separately
    if is_location_request:
        print("User requested location check.")
        return ChatResponse(
            reply="Đang xác định vị trí của bạn...",
            nearest_stores=[],
            trigger_location=True
        )
    
    # STEP 2: Check if we have a category
    if not search_intent or not search_intent.get('category'):
        # FALLBACK CASE 1: No category from AI Call #1
        print("DEBUG: No category found. Falling back to regex search across all products...")
        matched_products = regex_search_all_products(user_message)
        
        if len(matched_products) > 0:
            # Found products → Build store list → AI Call #3 for formatting
            print(f"DEBUG: Found {len(matched_products)} products via regex")
            
            # Get shops for these products
            shop_ids = matched_products['ID Shop'].unique()
            filtered_stores = stores_dataframe[
                stores_dataframe['store_id'].isin([str(sid) for sid in shop_ids])
            ]
            
            # Calculate distance and build response
            nearest_stores_data = find_nearest_stores(user_latitude, user_longitude, filtered_stores)
            nearest_stores_response = []
            
            for store in nearest_stores_data:
                store_products_df = matched_products[
                    matched_products['ID Shop'].astype(str) == str(store['store_id'])
                ]
                
                matching_products = []
                for _, row in store_products_df.head(5).iterrows():
                    matching_products.append(ProductInfo(
                        name=str(row.get('Tên sản phẩm', 'Sản phẩm')),
                        price=str(row.get('Giá niêm yết', 'Liên hệ')) if pd.notna(row.get('Giá niêm yết')) else "Liên hệ",
                        image_url=str(row.get('Link ảnh', '')) if pd.notna(row.get('Link ảnh')) else "",
                        link=str(row.get('Link sản phẩm', '')) if pd.notna(row.get('Link sản phẩm')) else ""
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
            
            # AI Call #3 to format response
            rich_store_data = [s.dict() for s in nearest_stores_response]
            ai_reply = await get_ai_response(user_message, rich_store_data, search_intent, 'product')
            
            return ChatResponse(
                reply=ai_reply,
                nearest_stores=nearest_stores_response
            )
        else:
            # No products found
            return ChatResponse(
                reply="Rất tiếc, em không tìm thấy sản phẩm phù hợp với yêu cầu của anh/chị. Anh/chị có thể thử tìm kiếm sản phẩm khác hoặc mô tả chi tiết hơn không ạ?",
                nearest_stores=[]
            )
    
    # STEP 3: We have a category → Filter products by category
    category_name = search_intent['category']
    
    # Fuzzy match category name
    import difflib
    matches = difflib.get_close_matches(category_name, unique_categories, n=1, cutoff=0.7)
    if matches:
        category_name = matches[0]
        print(f"DEBUG: Mapped AI category '{search_intent['category']}' to System category '{category_name}'")
    
    # Filter products by category
    category_products_df = products_dataframe[
        products_dataframe['Danh mục'].str.contains(category_name, case=False, na=False)
    ]
    
    print(f"DEBUG: Found {len(category_products_df)} products in category '{category_name}'")
    
    # Prepare data for AI Call #2 (only 2 columns: Tên SP, Tên Shop)
    category_products = []
    for _, row in category_products_df.iterrows():
        shop_id = str(row['ID Shop'])
        shop_row = stores_dataframe[stores_dataframe['store_id'] == shop_id]
        shop_name = shop_row['store_name'].iloc[0] if not shop_row.empty else "Unknown"
        
        category_products.append({
            "product_name": row['Tên sản phẩm'],
            "shop_name": shop_name
        })
    
    # Limit to 200 products to avoid token overflow
    category_products = category_products[:200]
    
    # STEP 4: AI Call #2 - Smart Product Filter + Template Generation
    try:
        ai_result = await smart_product_filter(user_message, category_products)
        
        if ai_result['found']:
            # SUCCESS PATH: AI found products
            print(f"DEBUG: AI Call #2 found {len(ai_result['products'])} products")
            
            selected_products = ai_result['products']
            
            # Get shop details and calculate distance
            shops_with_distance = []
            for prod in selected_products:
                shop_name = prod['shop_name']
                product_name = prod['product_name']
                
                # Find shop
                shop_row = stores_dataframe[stores_dataframe['store_name'] == shop_name]
                if shop_row.empty:
                    continue
                
                shop = shop_row.iloc[0]
                
                # Calculate distance
                distance = geodesic(
                    (user_latitude, user_longitude),
                    (shop['latitude'], shop['longitude'])
                ).km
                
                shops_with_distance.append({
                    'shop': shop,
                    'distance': distance,
                    'product_name': product_name
                })
            
            # Sort by distance
            shops_with_distance.sort(key=lambda x: x['distance'])
            
            if not shops_with_distance:
                raise ValueError("No valid shops found for selected products")
            
            # Deduplicate shops (keep closest occurrence of each shop)
            seen_shops = set()
            unique_shops = []
            for item in shops_with_distance:
                shop_id = item['shop']['store_id']
                if shop_id not in seen_shops:
                    seen_shops.add(shop_id)
                    unique_shops.append(item)
            
            shops_with_distance = unique_shops
            
            # Replace placeholders in template
            nearest = shops_with_distance[0]
            shop = nearest['shop']
            
            # Fetch product details
            product_row = products_dataframe[
                (products_dataframe['Tên sản phẩm'] == nearest['product_name']) &
                (products_dataframe['ID Shop'].astype(str) == str(shop['store_id']))
            ]
            
            price = "Liên hệ"
            image_url = ""
            if not product_row.empty:
                price = str(product_row['Giá niêm yết'].iloc[0]) if pd.notna(product_row['Giá niêm yết'].iloc[0]) else "Liên hệ"
                image_url = str(product_row['Link ảnh'].iloc[0]) if pd.notna(product_row['Link ảnh'].iloc[0]) else ""
            
            # Replace placeholders
            final_message = ai_result['ai_message_template']
            final_message = final_message.replace("{{product_name}}", nearest['product_name'])
            final_message = final_message.replace("{{shop_name}}", shop['store_name'])
            final_message = final_message.replace("{{distance}}", f"{nearest['distance']:.1f}")
            final_message = final_message.replace("{{address}}", shop['address'])
            final_message = final_message.replace("{{price}}", price)
            final_message = final_message.replace("{{image_url}}", image_url)
            final_message = final_message.replace("{{zalo_link}}", shop.get('zalo_group_link', ''))
            
            # Fallback: If template missing distance/price, append them
            if "{{distance}}" in ai_result['ai_message_template'] and "{{distance}}" in final_message:
                # Placeholder wasn't replaced (shouldn't happen but safety check)
                final_message = final_message.replace("{{distance}}", f"{nearest['distance']:.1f}")
            
            # If template doesn't mention distance or price at all, append info
            if 'km' not in final_message.lower():
                final_message += f" Shop cách bạn {nearest['distance']:.1f} km."
            if price != "Liên hệ" and price not in final_message:
                final_message += f" Giá {price}."

            
            # Build response with all shops
            nearest_stores_response = []
            for item in shops_with_distance[:5]:  # Top 5 shops
                shop = item['shop']
                
                # Get only AI-selected products for this shop
                ai_selected_for_shop = [
                    p for p in ai_result['products'] 
                    if p['shop_name'] == shop['store_name']
                ]
                
                matching_products = []
                for ai_product in ai_selected_for_shop:
                    # Find product details in dataframe
                    product_row = category_products_df[
                        (category_products_df['Tên sản phẩm'] == ai_product['product_name']) &
                        (category_products_df['ID Shop'].astype(str) == str(shop['store_id']))
                    ]
                    
                    if not product_row.empty:
                        row = product_row.iloc[0]
                        matching_products.append(ProductInfo(
                            name=str(row.get('Tên sản phẩm', 'Sản phẩm')),
                            price=str(row.get('Giá niêm yết', 'Liên hệ')) if pd.notna(row.get('Giá niêm yết')) else "Liên hệ",
                            image_url=str(row.get('Link ảnh', '')) if pd.notna(row.get('Link ảnh')) else "",
                            link=str(row.get('Link sản phẩm', '')) if pd.notna(row.get('Link sản phẩm')) else ""
                        ))
                
                nearest_stores_response.append(StoreInfo(
                    name=shop['store_name'],
                    address=shop['address'],
                    lat=shop['latitude'],
                    lng=shop['longitude'],
                    distance_km=item['distance'],
                    zalo_group_link=shop.get('zalo_group_link'),
                    products=matching_products
                ))
            
            return ChatResponse(
                reply=final_message,
                nearest_stores=nearest_stores_response
            )
        
        else:
            # FALLBACK CASE 2: AI Call #2 found nothing
            print("DEBUG: AI Call #2 found nothing. Falling back to regex...")
            matched_products = regex_search_all_products(user_message)
            
            if len(matched_products) > 0:
                # Same logic as FALLBACK CASE 1
                shop_ids = matched_products['ID Shop'].unique()
                filtered_stores = stores_dataframe[
                    stores_dataframe['store_id'].isin([str(sid) for sid in shop_ids])
                ]
                
                nearest_stores_data = find_nearest_stores(user_latitude, user_longitude, filtered_stores)
                nearest_stores_response = []
                
                for store in nearest_stores_data:
                    store_products_df = matched_products[
                        matched_products['ID Shop'].astype(str) == str(store['store_id'])
                    ]
                    
                    matching_products = []
                    for _, row in store_products_df.head(5).iterrows():
                        matching_products.append(ProductInfo(
                            name=str(row.get('Tên sản phẩm', 'Sản phẩm')),
                            price=str(row.get('Giá niêm yết', 'Liên hệ')) if pd.notna(row.get('Giá niêm yết')) else "Liên hệ",
                            image_url=str(row.get('Link ảnh', '')) if pd.notna(row.get('Link ảnh')) else "",
                            link=str(row.get('Link sản phẩm', '')) if pd.notna(row.get('Link sản phẩm')) else ""
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
                
                rich_store_data = [s.dict() for s in nearest_stores_response]
                ai_reply = await get_ai_response(user_message, rich_store_data, search_intent, 'product')
                
                return ChatResponse(
                    reply=ai_reply,
                    nearest_stores=nearest_stores_response
                )
            else:
                # No products found via regex → Fallback to category-based recommendation
                print(f"DEBUG: Regex found nothing. Falling back to category '{category_name}' recommendations...")
                
                # Get top 3 shops from this category
                category_shops = stores_dataframe[
                    stores_dataframe['categories'].str.contains(category_name, case=False, na=False)
                ]
                
                if not category_shops.empty:
                    nearest_stores_data = find_nearest_stores(user_latitude, user_longitude, category_shops, limit=3)
                    nearest_stores_response = []
                    
                    for store in nearest_stores_data:
                        # Get products for this shop in this category
                        store_products_df = category_products_df[
                            category_products_df['ID Shop'].astype(str) == str(store['store_id'])
                        ]
                        
                        matching_products = []
                        for _, row in store_products_df.head(5).iterrows():
                            matching_products.append(ProductInfo(
                                name=str(row.get('Tên sản phẩm', 'Sản phẩm')),
                                price=str(row.get('Giá niêm yết', 'Liên hệ')) if pd.notna(row.get('Giá niêm yết')) else "Liên hệ",
                                image_url=str(row.get('Link ảnh', '')) if pd.notna(row.get('Link ảnh')) else "",
                                link=str(row.get('Link sản phẩm', '')) if pd.notna(row.get('Link sản phẩm')) else ""
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
                    
                    # AI Call #3 to format response
                    rich_store_data = [s.dict() for s in nearest_stores_response]
                    ai_reply = await get_ai_response(user_message, rich_store_data, search_intent, 'category')
                    
                    return ChatResponse(
                        reply=ai_reply,
                        nearest_stores=nearest_stores_response
                    )
                else:
                    # No shops in category either
                    return ChatResponse(
                        reply="Rất tiếc, em không tìm thấy sản phẩm phù hợp với yêu cầu của anh/chị. Anh/chị có thể thử tìm kiếm sản phẩm khác hoặc mô tả chi tiết hơn không ạ?",
                        nearest_stores=[]
                    )
    
    except Exception as e:
        # FALLBACK CASE 3: AI Call #2 Error
        print(f"ERROR: AI Call #2 failed - {str(e)}")
        import logging
        logging.error(f"AI Call #2 error: {e}")
        
        return ChatResponse(
            reply="Xin lỗi anh/chị, hệ thống đang gặp sự cố kết nối. Vui lòng thử lại sau ít phút hoặc liên hệ bộ phận hỗ trợ ạ!",
            nearest_stores=[]
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
            
            print(f"DEBUG: Token Response Status: {token_response.status_code}")
            print(f"DEBUG: Token Response Body: {token_response.text}")
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
            
            # Build frontend URL dynamically from request
            # This works for both localhost and production domains
            frontend_url = "/index.html"  # Use relative path
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
