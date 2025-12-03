from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
import pandas as pd

from models import ChatRequest, ChatResponse, StoreInfo
from services.sheet_service import load_stores_data
from services.geo_service import find_nearest_stores
from services.ai_service import get_ai_response, extract_search_intent, configure_genai

# Force load .env from the project root
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(current_dir, "..")
env_path = os.path.join(project_root, ".env")

print(f"Loading .env from: {env_path}")
load_dotenv(env_path, override=True)

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
unique_categories: list[str] = []

@app.on_event("startup")
async def startup_event():
    global stores_dataframe, unique_categories
    print("Loading store data on startup...")
    stores_dataframe = load_stores_data()
    
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
            nearest_stores_response.append(StoreInfo(
                name=store['store_name'],
                address=store['address'],
                lat=store['latitude'],
                lng=store['longitude'],
                distance_km=store['distance_km']
            ))

    # 4. Generate AI Response
    ai_reply = await get_ai_response(user_message, nearest_stores_data, search_intent, match_type)

    return ChatResponse(
        reply=ai_reply, 
        nearest_stores=nearest_stores_response,
        trigger_location=is_location_request # Auto-trigger if user asked for location
    )

# Mount static files to serve frontend
# We serve the parent directory (project root) where index.html is located
# Place this AFTER all API routes to avoid shadowing
static_dir = os.path.join(os.path.dirname(__file__), "..")
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
