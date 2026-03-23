from geopy.distance import geodesic
from geopy.geocoders import Nominatim
import pandas as pd
import json
import os
import time
import random

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

def apply_jitter(lat, lng, amount=0.0003):
    """Apply small random offset to prevent marker overlap"""
    return lat + random.uniform(-amount, amount), lng + random.uniform(-amount, amount)

def geocode_address(address, cache=None, structured=None, expected_province=None):
    """
    Geocode address with province validation.
    expected_province: string to check against result's address details (e.g., "Vĩnh Phúc")
    """
    if not address and not structured:
        return None
        
    cache_key = str(structured) if structured else str(address)
    
    if cache is None:
        cache = load_cache()
        
    if cache_key in cache:
        return cache[cache_key]
        
    try:
        # We need addressdetails to validate province
        geolocator = Nominatim(user_agent="map_excel_api_chat_v3")
        
        if structured:
            location = geolocator.geocode(structured, timeout=10, addressdetails=True)
        else:
            location = geolocator.geocode(address + ", Vietnam", timeout=10, addressdetails=True)
        
        if location:
            # Validate Province if specified
            if expected_province:
                addr_details = location.raw.get('address', {})
                # Normalize expected province (handle D vs Ð and spaces)
                target = expected_province.lower().replace("ð", "đ").strip()
                
                # Check all common fields for province/city
                found_list = [
                    addr_details.get('state', ''),
                    addr_details.get('city', ''),
                    addr_details.get('province', ''),
                    addr_details.get('city_district', ''),
                    addr_details.get('state_district', ''),
                    addr_details.get('county', '')
                ]
                found_prov = " ".join(found_list).lower().replace("ð", "đ")
                
                # Mapping for special cases (Sub-cities or missing parent names)
                is_valid = target in found_prov
                if not is_valid:
                    # Aliases for Ho Chi Minh City
                    if target in ["hồ chí minh", "tp hcm", "tp.hcm", "hcm"]:
                        if any(x in found_prov for x in ["thủ đức", "sài gòn", "saigon", "quận", "hồ chí minh"]): is_valid = True
                    # Aliases for Da Nang
                    elif target == "đà nẵng":
                        if any(x in found_prov for x in ["cẩm lệ", "hải châu", "liên chiểu", "ngũ hành sơn", "sơn trà", "thanh khê", "đà nẵng"]): is_valid = True
                
                if not is_valid:
                    print(f"      🚫 Province Mismatch: Found '{found_prov.strip()}' but expected '{expected_province}'. Rejecting.")
                    return None

            result = (location.latitude, location.longitude)
            cache[cache_key] = result
            save_cache(cache)
            time.sleep(1)
            return result
        else:
            return None
    except Exception as e:
        print(f"!!! CRITICAL Geocoding error: {e}")
        return None

def find_nearest_stores(user_lat: float, user_long: float, stores_df: pd.DataFrame, limit: int = 3, max_distance_km: float = None):
    user_location = (user_lat, user_long)
    stores_with_distance = []

    for index, store in stores_df.iterrows():
        store_location = (store['latitude'], store['longitude'])
        try:
            distance = geodesic(user_location, store_location).km
        except ValueError:
            continue # Skip invalid coords

        # Filter by distance if specified
        if max_distance_km and distance > max_distance_km:
            continue

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
