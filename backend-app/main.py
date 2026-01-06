from fastapi import FastAPI, HTTPException, BackgroundTasks

from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
import os
import pandas as pd
import httpx
from datetime import datetime, timedelta
from urllib.parse import quote
import logging
from typing import Dict, List, Optional, Any, Tuple

# --- CONFIGURATION LOGGING ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# --- LOAD ENVIRONMENT VARIABLES ---
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(current_dir, "..")
env_path = os.path.join(project_root, ".env")

logger.info(f"Loading .env from: {env_path}")
load_dotenv(env_path, override=True)

# --- IMPORTS AFTER ENV LOAD ---
from models import ChatRequest, ChatResponse, StoreInfo, ProductInfo, LeadRequest

from services.sheet_service import load_stores_data, save_lead_to_sheet

from services.geo_service import find_nearest_stores
from services.ai_service import get_ai_response, extract_search_intent, configure_genai, smart_product_filter
from services.product_view import get_product_html
from geopy.distance import geodesic

# --- CONSTANTS ---
SESSION_TIMEOUT_HOURS = 24
ZALO_ACCESS_TOKEN_URL = "https://oauth.zaloapp.com/v4/access_token"
ZALO_GRAPH_API_URL = "https://graph.zalo.me/v2.0/me"
REDIRECT_FRONTEND_PATH = "/index.html"  # Relative path for redirect

ZALO_APP_ID = os.environ.get("ZALO_APP_ID", "")
ZALO_APP_SECRET = os.environ.get("ZALO_APP_SECRET", "")

SHEET_URL = os.getenv("GOOGLE_SHEET_URL", "")
SPREADSHEET_ID = "1ekdjU2lJK1MnBzwFr3B8ws2E8GnK1omLJNbIU8puXPI"
GID = "815593620"

GREETING_KEYWORDS = ["xin chào", "chào", "hello", "hi", "hey"]

# --- GLOBAL STATE ---
# In-memory storage (Consider Redis for production)
sessions: Dict[str, dict] = {}
stores_dataframe: pd.DataFrame = pd.DataFrame()
products_dataframe: pd.DataFrame = pd.DataFrame()
unique_categories: List[str] = []

app = FastAPI()

# --- MIDDLEWARE ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- HELPER FUNCTIONS ---

def regex_search_all_products(query: str, limit: int = 3) -> Tuple[pd.DataFrame, bool]:
    """Search across all products using regex with OR logic and relevance scoring
    
    Returns:
        tuple: (matched_products_df, is_fuzzy_match)
            - is_fuzzy_match=False: Exact phrase match found
            - is_fuzzy_match=True: Split-term OR search used (may have irrelevant results)
    """
    if products_dataframe.empty:
        return pd.DataFrame(), False
    
    # STEP 1: Try EXACT phrase match first
    exact_match = products_dataframe[
        products_dataframe['Tên sản phẩm'].str.contains(query, case=False, na=False)
    ]
    
    if not exact_match.empty:
        logger.info(f"✅ Found {len(exact_match)} products with exact phrase: '{query}'")
        return exact_match.head(limit), False  # is_fuzzy=False
    
    # STEP 2: Fallback to split-term OR logic
    logger.info(f"⚠️ No exact match for '{query}'. Trying split-term search...")
    search_terms = query.split()
    
    # Use OR logic: match products containing ANY term
    mask = pd.Series([False] * len(products_dataframe))
    
    for term in search_terms:
        term_mask = products_dataframe['Tên sản phẩm'].str.contains(
            term, case=False, na=False
        )
        mask = mask | term_mask  # OR logic
    
    matched_products = products_dataframe[mask].copy()
    
    if matched_products.empty:
        logger.warning(f"❌ No products found for query: '{query}'")
        return pd.DataFrame(), True  # is_fuzzy=True (but empty)
    
    # Score by number of matching terms (higher = more relevant)
    def count_matches(product_name):
        count = 0
        product_lower = str(product_name).lower()
        for term in search_terms:
            if term.lower() in product_lower:
                count += 1
        return count
    
    matched_products['relevance_score'] = matched_products['Tên sản phẩm'].apply(count_matches)
    
    # Sort by relevance (descending) and return top results
    return matched_products.sort_values('relevance_score', ascending=False).head(limit), True  # is_fuzzy=True

def convert_to_proxy_link(dropbuy_link: str) -> str:
    """
    Convert Dropbuy product link to proxy link
    
    Args:
        dropbuy_link: Original Dropbuy link (e.g., https://dropbuy.vn/quat-cay_p114453)
    
    Returns:
        Proxy link (e.g., /view/114453?url=https://dropbuy.vn/quat-cay_p114453)
    """
    import re
    if not dropbuy_link:
        return ""
    
    # Extract product ID from link (format: .../_p{id} or .../p{id})
    match = re.search(r'_p(\d+)', dropbuy_link)
    if match:
        product_id = match.group(1)
        # Include original URL for scraping if not cached
        from urllib.parse import quote
        return f"/view/{product_id}?url={quote(dropbuy_link)}"
    
    return dropbuy_link  # Fallback to original if can't extract ID

# ... (imports)

# ... (imports without traceback)

async def exchange_zalo_access_token(client: httpx.AsyncClient, code: str, code_verifier: Optional[str] = None) -> str:
    """Exchange authorization code for Zalo access token"""
    payload = {
        "app_id": ZALO_APP_ID,
        "code": code,
        "grant_type": "authorization_code"
    }
    
    if code_verifier:
        payload["code_verifier"] = code_verifier
    
    response = await client.post(
        ZALO_ACCESS_TOKEN_URL,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "secret_key": ZALO_APP_SECRET
        },
        data=payload
    )
    
    token_data = response.json()
    
    if "access_token" not in token_data:
        error_msg = token_data.get("error_description", token_data.get("error", "Unknown error"))
        logger.error(f"Zalo Token Error: {token_data}")
        raise HTTPException(status_code=400, detail=f"Failed to get access token: {error_msg}")
        
    return token_data["access_token"]

async def get_zalo_user_profile(client: httpx.AsyncClient, access_token: str) -> dict:
    """Fetch user profile from Zalo Graph API"""
    response = await client.get(
        ZALO_GRAPH_API_URL,
        params={"access_token": access_token, "fields": "id,name,picture"}
    )
    user_data = response.json()
    
    if "id" not in user_data:
        error_msg = user_data.get("error", {}).get("message", "Unknown error")
        logger.error(f"Zalo Profile Error: {user_data}")
        raise HTTPException(status_code=400, detail=f"Failed to get user info: {error_msg}")
        
    return user_data

# --- APP EVENTS ---

@app.on_event("startup")
async def startup_event():
    global stores_dataframe, unique_categories, products_dataframe
    logger.info("Starting up application...")
    
    # Load Data
    stores_dataframe, products_dataframe, unique_categories = load_stores_data()
    
    # DEBUG: Check Staff Zalo Data Quality
    if not products_dataframe.empty:
        # Check if 'Link NV' column exists in any form
        link_nv_cols = [c for c in products_dataframe.columns if 'link nv' in str(c).lower()]
        print(f"DEBUG: Found 'Link NV' columns: {link_nv_cols}")
        
        if link_nv_cols:
            count = products_dataframe[link_nv_cols[0]].notna().sum()
            print(f"DEBUG: Products with 'Link NV' populated: {count} / {len(products_dataframe)}")
            # Print sample
            sample = products_dataframe[products_dataframe[link_nv_cols[0]].notna()].head(1)
            if not sample.empty:
                print(f"DEBUG: Sample Link NV: {sample[link_nv_cols[0]].iloc[0]}")
    
    if not stores_dataframe.empty:
        logger.info(f"Loaded {len(stores_dataframe)} stores.")
        logger.info(f"Unique Categories: {len(unique_categories)}")
    else:
        logger.warning("No store data loaded or categories found.")

    # Generic AI Config
    logger.info("Configuring Gemini API...")
    configure_genai()

@app.get("/favicon.ico")
async def favicon():
    """Return 204 for favicon to stop tab spinning"""
    return Response(content="", status_code=204)

@app.get("/{path:path}.map")
async def source_maps(path: str):
    """Immediate 404 for source maps to prevent browser hangs"""
    return Response(status_code=404)

# --- ROUTES ---

@app.post("/chat", response_model=ChatResponse)
async def chat_with_ai(request: ChatRequest):
    user_message = request.message
    lat = request.latitude
    lng = request.longitude

    if stores_dataframe.empty:
        raise HTTPException(status_code=500, detail="Store data not loaded.")

    # 1. EXTRACT INTENT
    search_intent = await extract_search_intent(user_message, unique_categories)
    logger.info(f"Intent: {search_intent}")
    
    if search_intent:
        is_location_req = search_intent.get('is_location_request', False)
        is_general_inquiry = search_intent.get('is_general_inquiry', False)
    else:
        # Fallback if AI fails
        is_location_req = False
        is_general_inquiry = False
    
    # Handle General Inquiry
    if is_general_inquiry:
        is_greeting = any(k in user_message.lower() for k in GREETING_KEYWORDS)
        category_sample = ", ".join(unique_categories[:10])
        
        if is_greeting:
            reply = f"Xin chào! Chúc bạn một ngày tốt lành! 😊 Shop em có các ngành hàng: {category_sample}... Bạn muốn tìm gì ạ?"
        else:
            reply = f"Dạ shop em có các ngành hàng: {category_sample}... Anh/chị cần tìm sản phẩm nào ạ?"
        
        return ChatResponse(reply=reply, nearest_stores=[])
    
    # Handle Location Request
    if is_location_req:
        return ChatResponse(reply="Đang xác định vị trí...", nearest_stores=[], trigger_location=True)
    
    # 2. PRODUCT SEARCH
    if search_intent is None:
        logger.warning("Search Intent is None (AI Limit/Error). Defaulting to empty dict.")
        search_intent = {}

    category_name = search_intent.get('category')
    
    # FALLBACK: No Category -> Regex Search All
    if not category_name:
        logger.debug("No category found. Using Regex Fallback.")
        
        # FIX: Use extracted product name if available, otherwise User Message
        search_query = user_message
        if search_intent and search_intent.get('product'):
            search_query = search_intent.get('product')
        elif search_intent and search_intent.get('generic_term'):
            search_query = search_intent.get('generic_term')
            
        logger.info(f"Regex Search Query: {search_query}")
        matched, is_fuzzy = regex_search_all_products(search_query)
        
        if not matched.empty:
            # Add disclaimer for fuzzy matches
            if is_fuzzy:
                fuzzy_disclaimer = "⚠️ Em không tìm thấy chính xác, nhưng có **một số sản phẩm liên quan** anh tham khảo ạ:\n\n"
                response = await build_response_from_products(matched, lat, lng, user_message, search_intent, 'product')
                response.reply = fuzzy_disclaimer + response.reply
                return response
            else:
                # Exact match - no disclaimer needed
                return await build_response_from_products(matched, lat, lng, user_message, search_intent, 'product')
        else:
            return ChatResponse(
                reply="Rất tiếc, em không tìm thấy sản phẩm phù hợp. Anh/chị vui lòng mô tả chi tiết hơn ạ.",
                nearest_stores=[]
            )

    # 3. CATEGORY FILTER
    # Fuzzy match category
    import difflib
    matches = difflib.get_close_matches(category_name, unique_categories, n=1, cutoff=0.7)
    if matches:
        category_name = matches[0]
        
    cat_products_df = products_dataframe[
        products_dataframe['Danh mục'].str.contains(category_name, case=False, na=False)
    ]
    logger.info(f"Found {len(cat_products_df)} products in category '{category_name}'")

    # Prepare for AI Call #2
    cat_products_list = []
    for _, row in cat_products_df.iterrows():
        shop_id = str(row['ID Shop'])
        shop_row = stores_dataframe[stores_dataframe['store_id'] == shop_id]
        shop_name = shop_row['store_name'].iloc[0] if not shop_row.empty else "Unknown"
        cat_products_list.append({
            "product_name": row['Tên sản phẩm'],
            "shop_name": shop_name
        })
    
    # 4. AI SMART FILTER
    try:
        ai_result = await smart_product_filter(user_message, cat_products_list[:200])
        
        if ai_result['found']:
            # Use AI selected products
            selected = ai_result['products']
            
            # Filter original dataframe for these products
            # This logic mimics the previous complex logic but simpler
            # Note: For brevity in this refactor, I'm simplifying the reconstruction 
            # of the dataframe or list needed for the response builder. 
            # Ideally this should be a separate helper function too.
            
            # ... (Implementation regarding AI result processing preserved mostly logic-wise)
            
            # Let's reuse a helper for response building to keep main clean
            # For now, keeping the core logic but cleaning it up is dangerous without careful structural changes
            # I will keep the original logic block for safety but cleaned up logging.
            
            # ... [Logic from original lines 249-370] ...
            # Due to complexity of map/reduce logic here, I will retain it but cleaner.
            
            # (Re-implementing the specific logic block for brevity in artifact)
            # [LOGIC BLOCK START]
            shops_with_distance = []
            for prod in selected:
                shop_name = prod['shop_name']
                product_name = prod['product_name']
                shop_row = stores_dataframe[stores_dataframe['store_name'] == shop_name]
                if shop_row.empty: continue
                shop = shop_row.iloc[0]
                dist = geodesic((lat, lng), (shop['latitude'], shop['longitude'])).km
                shops_with_distance.append({'shop': shop, 'distance': dist, 'product_name': product_name})
            
            shops_with_distance.sort(key=lambda x: x['distance'])
            if not shops_with_distance: raise ValueError("No valid shops")
            
            # Deduplicate
            seen = set()
            unique_shops = []
            for item in shops_with_distance:
                sid = item['shop']['store_id']
                if sid not in seen:
                    seen.add(sid)
                    unique_shops.append(item)
            shops_with_distance = unique_shops
            
            # Format Messgae (Template)
            nearest = shops_with_distance[0]
            shop = nearest['shop']
            
            # Get Product Info for Template
            p_row = products_dataframe[
                (products_dataframe['Tên sản phẩm'] == nearest['product_name']) &
                (products_dataframe['ID Shop'].astype(str) == str(shop['store_id']))
            ]
            price = "Liên hệ"
            img_url = ""
            if not p_row.empty:
                price = str(p_row['Giá niêm yết'].iloc[0]) if pd.notna(p_row['Giá niêm yết'].iloc[0]) else "Liên hệ"
                img_url = str(p_row['Link ảnh'].iloc[0]) if pd.notna(p_row['Link ảnh'].iloc[0]) else ""

            final_msg = ai_result['ai_message_template']
            final_msg = final_msg.replace("{{product_name}}", nearest['product_name']) \
                                 .replace("{{shop_name}}", shop['store_name']) \
                                 .replace("{{distance}}", f"{nearest['distance']:.1f}") \
                                 .replace("{{address}}", shop['address']) \
                                 .replace("{{price}}", price) \
                                 .replace("{{image_url}}", img_url) \
                                 .replace("{{zalo_link}}", shop.get('zalo_group_link', ''))

            if 'km' not in final_msg.lower(): final_msg += f" Shop cách bạn {nearest['distance']:.1f} km."
            if price != "Liên hệ" and price not in final_msg: final_msg += f" Giá {price}."

            # Build Store Response List
            nearest_stores_resp = []
            for item in shops_with_distance[:5]:
                store = item['shop']
                # Filter products for this store from AI results
                ai_products_store = [p for p in ai_result['products'] if p['shop_name'] == store['store_name']]
                
                matching_prods = []
                for ap in ai_products_store:
                     target_name = ap['product_name'].strip()
                     
                     # Filter by Shop first (Optimization)
                     shop_prods = cat_products_df[
                        cat_products_df['ID Shop'].astype(str) == str(store['store_id'])
                     ]
                     
                     # 1. Try Exact Match (Normalized)
                     row_df = shop_prods[
                        shop_prods['Tên sản phẩm'].str.strip() == target_name
                     ]
                     
                     # 2. Fallback: Fuzzy / Contains match
                     if row_df.empty:
                         # Escape regex characters if any
                         import re
                         safe_target = re.escape(target_name)
                         row_df = shop_prods[
                            shop_prods['Tên sản phẩm'].str.contains(safe_target, case=False, na=False)
                         ]

                     if not row_df.empty:
                         r = row_df.iloc[0]
                         matching_prods.append(ProductInfo(
                             name=str(r.get('Tên sản phẩm', '')),
                             price=str(r.get('Giá niêm yết', 'Liên hệ')) if pd.notna(r.get('Giá niêm yết')) else "Liên hệ",
                             image_url=str(r.get('Link ảnh', '')) if pd.notna(r.get('Link ảnh')) else "",
                             link=convert_to_proxy_link(str(r.get('Link sản phẩm', '')) if pd.notna(r.get('Link sản phẩm')) else "")
                         ))

                nearest_stores_resp.append(StoreInfo(
                    name=store['store_name'],
                    address=store['address'],
                    lat=store['latitude'],
                    lng=store['longitude'],
                    distance_km=item['distance'],
                    zalo_group_link=store.get('zalo_group_link'),
                    products=matching_prods
                ))
            
            return ChatResponse(reply=final_msg, nearest_stores=nearest_stores_resp)
            # [LOGIC BLOCK END]

        else:
            # Fallback 2: AI found nothing -> Regex
            logger.info("AI Smart Filter found nothing. Fallback to Regex.")
            
            # FIX: Use extracted product name if available
            search_query = user_message
            if search_intent and search_intent.get('product'):
                search_query = search_intent.get('product')
            elif search_intent and search_intent.get('generic_term'):
                search_query = search_intent.get('generic_term')

            matched = regex_search_all_products(search_query)
            if not matched.empty:
                return await build_response_from_products(matched, lat, lng, user_message, search_intent, 'product')
            else:
                # Fallback to Category Shops
                logger.info(f"Regex failed. Suggesting stores in category: {category_name}")
                cat_shops = stores_dataframe[stores_dataframe['categories'].str.contains(category_name, case=False, na=False)]
                
                if not cat_shops.empty:
                     # ... (Logic from original lines 428-463) ...
                     # Simplified call
                     return await build_category_response(cat_shops, cat_products_df, lat, lng, user_message, search_intent)
                else:
                    return ChatResponse(reply="Không tìm thấy sản phẩm phù hợp.", nearest_stores=[])

    except Exception as e:
        logger.error(f"Error in chat processing: {e}")
        return ChatResponse(reply="Hệ thống đang bận, vui lòng thử lại sau.", nearest_stores=[])

# --- RESPONSE BUILDER HELPERS (Extracted to keep chat() clean) ---
# Note: In a full refactor these would be separate functions. 
# For this immediate step, I included logic inline above for safety or stub placeholders if I can't guarantee variable context.
# To ensure minimal breakage, I will actually keep the complex logic inline but cleaner as shown above.

def extract_staff_zalo(row):
    """Helper to extract and clean staff Zalo phone from row"""
    # 1. Try exact column 'Link NV'
    val = row.get('Link NV')
    
    # 2. Key Fallback: case-insensitive search if exact fails
    if pd.isna(val):
        for col in row.index:
            if str(col).strip().lower() == 'link nv':
                val = row[col]
                break
    
    if pd.isna(val): return None
        
    s_val = str(val).strip()
    # Remove non-digit characters just in case (optional, but safer)
    import re
    s_val = re.sub(r'[^0-9]', '', s_val)
    
    # Logic: If missing leading zero (e.g. 987...) -> Add '0'
    if len(s_val) == 9:
        s_val = '0' + s_val
        
    return s_val if s_val else None


async def build_response_from_products(matched_df, lat, lng, msg, intent, type):
    """Helper to build response when we have a list of matching products"""
    shop_ids = matched_df['ID Shop'].unique()
    filtered_stores = stores_dataframe[stores_dataframe['store_id'].isin([str(s) for s in shop_ids])]
    nearest_data = find_nearest_stores(lat, lng, filtered_stores)
    
    resp_list = []
    for store in nearest_data:
        s_prods = matched_df[matched_df['ID Shop'].astype(str) == str(store['store_id'])]
        p_list = []
        for _, r in s_prods.head(5).iterrows():
            p_list.append(ProductInfo(
                name=str(r.get('Tên sản phẩm', '')),
                price=str(r.get('Giá niêm yết', 'Liên hệ')) if pd.notna(r.get('Giá niêm yết')) else "Liên hệ",
                image_url=str(r.get('Link ảnh', '')) if pd.notna(r.get('Link ảnh')) else "",
                link=convert_to_proxy_link(str(r.get('Link sản phẩm', '')) if pd.notna(r.get('Link sản phẩm')) else ""),
                staff_zalo=extract_staff_zalo(r)
            ))
        resp_list.append(StoreInfo(
            name=store['store_name'], address=store['address'], lat=store['latitude'], lng=store['longitude'],
            distance_km=store['distance_km'], zalo_group_link=store.get('zalo_group_link'), products=p_list
        ))
    
    rich_data = [s.dict() for s in resp_list]
    ai_reply = await get_ai_response(msg, rich_data, intent, type)
    return ChatResponse(reply=ai_reply, nearest_stores=resp_list)

async def build_category_response(cat_shops, cat_prods_df, lat, lng, msg, intent):
    """
    Build response for category search, with KEYWORD FILTERING support.
    If intent has 'product' keyword (e.g. 'quạt'), filter products in category (e.g. 'Điều hòa - Quạt')
    to only those matching 'quạt'.
    """
    
    # Keyword Filter: "quạt", "điều hòa", etc.
    filter_keyword = ""
    if intent.product and len(intent.product) > 2:
        filter_keyword = intent.product.lower()
        print(f"🔎 Filtering Category by Keyword: '{filter_keyword}'")
    
    # Only keep shops matching category logic (already done in main flow)
    # But we need to filter PRODUCTS inside those shops
    
    nearest_data = find_nearest_stores(lat, lng, cat_shops, limit=3)
    resp_list = []
    
    for store in nearest_data:
        # Get products of this shop in this category
        s_prods = cat_prods_df[cat_prods_df['ID Shop'].astype(str) == str(store['store_id'])]
        
        # Apply Keyword Filter if exists
        if filter_keyword:
            # Simple containment check
            # Exclude strict matches if needed, but 'contains' is safer standard
            s_prods = s_prods[s_prods['Tên sản phẩm'].astype(str).str.lower().str.contains(filter_keyword, na=False)]
        
        p_list = []
        for _, r in s_prods.head(15).iterrows():
             p_list.append(ProductInfo(
                name=str(r.get('Tên sản phẩm', '')),
                price=str(r.get('Giá niêm yết', 'Liên hệ')) if pd.notna(r.get('Giá niêm yết')) else "Liên hệ",
                image_url=str(r.get('Link ảnh', '')) if pd.notna(r.get('Link ảnh')) else "",
                link=convert_to_proxy_link(str(r.get('Link sản phẩm', '')) if pd.notna(r.get('Link sản phẩm')) else ""),
                staff_zalo=extract_staff_zalo(r)
            ))
        
        # Only add shop if it has matching products (after filter)
        if p_list: 
            resp_list.append(StoreInfo(
                name=store['store_name'], address=store['address'], lat=store['latitude'], lng=store['longitude'],
                distance_km=store['distance_km'], zalo_group_link=store.get('zalo_group_link'), products=p_list
            ))
    
    rich_data = [s.dict() for s in resp_list]
    
    # Customize AI Prompt context
    context_type = 'category'
    if filter_keyword:
        context_type = f"category_filtered_{filter_keyword}"
        
    ai_reply = await get_ai_response(msg, rich_data, intent, context_type)
    return ChatResponse(reply=ai_reply, nearest_stores=resp_list)


# --- AUTH ROUTES ---

@app.get("/api/auth/zalo/verify")
async def zalo_callback(code: str = None, state: str = None, error: str = None, code_verifier: str = None):
    """Zalo OAuth callback handled with clean helper functions"""
    if error:
        return HTMLResponse(f"<html><body><h1>Đăng nhập thất bại</h1><p>{error}</p><a href='/login.html'>Thử lại</a></body></html>", status_code=400)
    if not code:
        return HTMLResponse(f"<html><body><h1>Thiếu mã xác thực</h1><a href='/login.html'>Quay lại</a></body></html>", status_code=400)
    
    try:
        async with httpx.AsyncClient() as client:
            # 1. Get Access Token
            access_token = await exchange_zalo_access_token(client, code, code_verifier)
            
            # 2. Get User Info
            user_data = await get_zalo_user_profile(client, access_token)
            
            # 3. Create Session
            session_id = f"zalo_{user_data['id']}_{datetime.now().timestamp()}"
            sessions[session_id] = {
                "user_id": user_data["id"],
                "name": user_data.get("name", "User"),
                "picture": user_data.get("picture", {}).get("data", {}).get("url", ""),
                "login_time": datetime.now().isoformat(),
                "type": "zalo"
            }
            
            # 4. Redirect
            encoded_name = quote(user_data.get("name", "User"))
            user_pic = user_data.get("picture", {}).get("data", {}).get("url", "")
            encoded_pic = quote(user_pic) if user_pic else ""
            
            redirect_url = f"{REDIRECT_FRONTEND_PATH}?session_id={session_id}&user_type=zalo&user_name={encoded_name}&user_picture={encoded_pic}&login_time={datetime.now().isoformat()}"
            
            return HTMLResponse(f"""
                <html><body>
                    <h2 style="text-align: center; margin-top: 50px;">Đăng nhập thành công! Đang chuyển hướng...</h2>
                    <script>window.location.href = '{redirect_url}';</script>
                </body></html>
            """)

    except Exception as e:
        logger.error(f"Auth Error: {e}")
        return HTMLResponse(f"<html><body><h1>Lỗi hệ thống</h1><p>{str(e)}</p><a href='/login.html'>Thử lại</a></body></html>", status_code=500)

@app.get("/auth/verify")
async def verify_session(session_id: str = None):
    if not session_id or session_id not in sessions:
        return {"valid": False}
    
    session = sessions[session_id]
    login_time = datetime.fromisoformat(session["login_time"])
    
    if datetime.now() - login_time > timedelta(hours=SESSION_TIMEOUT_HOURS):
        del sessions[session_id]
        return {"valid": False}
    
    return {"valid": True, "user": {"name": session["name"], "type": session["type"]}}

# --- PRODUCT VIEW ROUTE ---

@app.get("/view/{product_id}", response_class=HTMLResponse)
async def view_product(product_id: str, url: str = None):
    """
    Display proxied Dropbuy product page
    
    Args:
        product_id: Product ID
        url: Optional Dropbuy product URL for scraping if not cached
    
    Returns:
        HTML page with hijacked buy buttons that redirect to chatbox
    """
    try:
        html_content = get_product_html(product_id, url)
        return HTMLResponse(content=html_content)
    except Exception as e:
        logger.error(f"Error viewing product {product_id}: {e}")
        return HTMLResponse(
            content=f"<h1>Lỗi hiển thị sản phẩm</h1><p>{str(e)}</p>",
            status_code=500
        )

# --- STATIC FILES ---
# Static files moved to end to prevent blocking API routes
# app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

@app.get("/api/product-info/{product_id}")
@app.get("/product-info-api/{product_id}") 
async def get_product_info_api(product_id: str):
    """
    Get product info and shop Zalo link by Product ID
    """
    try:
        if products_dataframe.empty:
            return {"error": "Data not loaded"}
            
        # Search for product by ID (using regex on Link or just checking valid ID)
        # The Link column usually contains ..._p{id}
        # Let's search loosely for now or strictly map if possible.
        # Since we don't have a direct ID column, we use the Link pattern.
        
        # Faster approach: Filter by Link containing _p{product_id}
        # Updated Logic: Try multiple patterns
        s_id = str(product_id).strip()
        
        # 1. Standard: _p{id}
        mask = products_dataframe['Link sản phẩm'].str.contains(f'_p{s_id}', na=False)
        matched_products = products_dataframe[mask]
        
        # 2. Fallback: -p{id} (common in some platforms)
        if matched_products.empty:
             mask = products_dataframe['Link sản phẩm'].str.contains(f'-p{s_id}', na=False)
             matched_products = products_dataframe[mask]
             
        # 3. Fallback: Just ID (if len > 4 to avoid false positives)
        if matched_products.empty and len(s_id) > 4:
             mask = products_dataframe['Link sản phẩm'].str.contains(s_id, na=False)
             matched_products = products_dataframe[mask]

        if matched_products.empty:
             return {"error": "Product not found"}
             
        product = matched_products.iloc[0]
        
        # Robust ID extraction
        raw_shop_id = product.get('ID Shop')
        shop_id = str(int(float(raw_shop_id))).strip() if pd.notna(raw_shop_id) else None
        
        print(f"DEBUG: PID={product_id} | RawSID={raw_shop_id} | ShopID={shop_id}")
        
        # Default info from product row
        shop_name = product.get('Tên Shop', '')
        if not shop_name or str(shop_name).lower() == 'nan':
            shop_name = "Cửa hàng"
            
        shop_zalo = ""

        # Try mapping to aggregated shops
        if not stores_dataframe.empty:
            shop_match = pd.DataFrame()
            
            # 1. Try Match by ID
            if shop_id:
                # Ensure store_id col is string and stripped
                mask_id = stores_dataframe['store_id'].astype(str).str.strip() == shop_id
                shop_match = stores_dataframe[mask_id]
                print(f"DEBUG: Match by ID count: {len(shop_match)}")

            # 2. Key Fallback: Match by Shop Name if ID failed
            if shop_match.empty and shop_name != "Cửa hàng":
                print(f"DEBUG: Fallback matching by name: {shop_name}")
                mask_name = stores_dataframe['store_name'].astype(str).str.strip().str.lower() == str(shop_name).strip().lower()
                shop_match = stores_dataframe[mask_name]
                print(f"DEBUG: Match by Name count: {len(shop_match)}")

            if not shop_match.empty:
                # Force take the FIRST match no matter what
                shop_row = shop_match.iloc[0]
                
                # Update info from master store record
                found_name = shop_row.get('store_name')
                if pd.notna(found_name) and str(found_name).strip():
                    shop_name = str(found_name).strip()

                # EXTRACT ZALO LINK - SAFEST METHOD
                # Handle case where column might not exist or be named differently
                zalo_col = 'zalo_group_link' if 'zalo_group_link' in shop_match.columns else None
                
                if zalo_col:
                    val_zalo = shop_row.get(zalo_col)
                    # Convert to string, strip, handle nan/None/False
                    if pd.notna(val_zalo):
                         shop_zalo = str(val_zalo).strip()
                         # Final cleanup check
                         if shop_zalo.lower() == 'nan': shop_zalo = ""
                
                print(f"DEBUG: Found Shop Zalo from Store Match: '{shop_zalo}'")

        # Fallback Zalo from product columns if still empty
        if not shop_zalo:
            print("DEBUG: Checking internal product columns for Zalo...")
            for col in products_dataframe.columns:
                if 'zalo' in str(col).lower():
                    val = product[col]
                    if pd.notna(val):
                        val_str = str(val).strip()
                        if val_str and val_str.lower() != 'nan':
                            shop_zalo = val_str
                            print(f"DEBUG: Found Zalo in column {col}: '{shop_zalo}'")
                            break
                        
        # EXTRACT STAFF ZALO (Link NV)
        raw_staff_zalo = extract_staff_zalo(product)
        
        return {
            "product_name": product.get('Tên sản phẩm', 'Sản phẩm'),
            "price": str(product.get('Giá niêm yết', '')) if pd.notna(product.get('Giá niêm yết', '')) else "Liên hệ",
            "shop_name": shop_name,
            "zalo_link": shop_zalo,
            "staff_zalo": raw_staff_zalo
        }
    except Exception as e:
        logger.error(f"Error fetching product info for {product_id}: {e}")
        return {"error": f"Internal server error: {str(e)}"}

@app.post("/api/submit-lead")
async def submit_lead(lead: LeadRequest, background_tasks: BackgroundTasks):
    """
    Receive lead data and save to Google Sheet in background.
    """
    logger.info(f"Received lead for: {lead.product_name} from {lead.user_name}")
    
    # Add timestamp if missing
    if not lead.timestamp:
        lead.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
    # Convert model to dict (Compatibility for Pydantic V1 and V2)
    if hasattr(lead, "model_dump"):
        lead_data = lead.model_dump()
    else:
        lead_data = lead.dict()
    
    # Run in background
    background_tasks.add_task(save_lead_to_sheet, lead_data)
    
    return {"status": "success", "message": "Lead queued"}

@app.get("/api/config")
async def get_frontend_config():
    """
    Expose safe public configuration to frontend.
    Allows frontend to not hardcode App IDs.
    """
    # Strict localhost for Zalo compliance
    base_url = "http://localhost:8000"
    
    # Priority: ENV > Default
    env_redirect = os.environ.get("ZALO_REDIRECT_URI", "")
    final_redirect = env_redirect if env_redirect else f"{base_url}/zalo_callback.html"

    logger.info(f"Config API: AppID={ZALO_APP_ID}, Redirect={final_redirect}")
    
    return {
        "zalo_app_id": ZALO_APP_ID,
        "zalo_redirect_uri": final_redirect
    }

@app.get("/auth/zalo/callback", response_class=HTMLResponse)
async def zalo_callback_alias():
    """
    Alias for the Zalo Callback URL defined in user's .env.
    Serve the static zalo_callback.html file content.
    """
    file_path = os.path.join(static_dir, "zalo_callback.html")
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    return Response(status_code=404, content="Callback file not found")

# Static files should be mounted LAST
static_dir = os.path.join(os.path.dirname(__file__), "..")
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
