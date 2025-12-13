from geopy.distance import geodesic
from geopy.geocoders import Nominatim
import pandas as pd
import json
import os
import time

# Cache file path
CACHE_FILE = 'geocoding_cache.json'

def load_cache():
    """Load geocoding cache from disk"""
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_cache(cache):
    """Save geocoding cache to disk"""
    try:
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving cache: {e}")

def build_address(ward, district, city):
    """Build full address string from components"""
    components = []
    if pd.notna(ward) and str(ward).strip():
        components.append(str(ward).strip())
    if pd.notna(district) and str(district).strip():
        components.append(str(district).strip())
    if pd.notna(city) and str(city).strip():
        components.append(str(city).strip())
    
    return ", ".join(components)

def geocode_address(address, cache=None):
    """Geocode address to (lat, lng)"""
    if not address or not isinstance(address, str):
        return None
        
    if cache is None:
        cache = load_cache()
        
    if address in cache:
        return cache[address]
        
    try:
        geolocator = Nominatim(user_agent="map_excel_api_chat_v3")
        location = geolocator.geocode(address + ", Vietnam", timeout=10)
        
        if location:
            result = (location.latitude, location.longitude)
            # Update cache
            cache[address] = result
            save_cache(cache)
            time.sleep(1) # Rate limiting
            return result
        else:
            print(f"Could not geocode: {address}")
            return None
    except Exception as e:
        print(f"Geocoding error for {address}: {e}")
        return None

def find_nearest_stores(user_lat: float, user_long: float, stores_df: pd.DataFrame, limit: int = 3):
    user_location = (user_lat, user_long)
    stores_with_distance = []

    for index, store in stores_df.iterrows():
        store_location = (store['latitude'], store['longitude'])
        try:
            distance = geodesic(user_location, store_location).km
        except ValueError:
            continue # Skip invalid coords

        stores_with_distance.append({
            "store_id": store['store_id'],
            "store_name": store['store_name'],
            "address": store['address'],
            "category": store['category'],
            "product_info": store['product_info'],
            "promotion": store['promotion'],
            "latitude": store['latitude'],
            "longitude": store['longitude'],
            "zalo_group_link": store.get('zalo_group_link', ''),
            "products": store.get('products', []), # Include products
            "distance_km": distance
        })
    
    # Sort by distance
    stores_with_distance.sort(key=lambda x: x['distance_km'])
    
    # Return top 'limit' stores
    return stores_with_distance[:limit]

if __name__ == '__main__':
    pass
