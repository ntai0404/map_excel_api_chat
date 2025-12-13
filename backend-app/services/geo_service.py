from geopy.distance import geodesic
import pandas as pd

def find_nearest_stores(user_lat: float, user_long: float, stores_df: pd.DataFrame, limit: int = 3):
    user_location = (user_lat, user_long)
    stores_with_distance = []

    for index, store in stores_df.iterrows():
        store_location = (store['latitude'], store['longitude'])
        distance = geodesic(user_location, store_location).km

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
            "distance_km": distance
        })
    
    # Sort by distance
    stores_with_distance.sort(key=lambda x: x['distance_km'])
    
    # Return top 'limit' stores
    return stores_with_distance[:limit]

if __name__ == '__main__':
    # Example usage (for testing purposes)
    # Create a dummy DataFrame for testing
    data = [
        {"store_id": "1", "store_name": "Shop A", "address": "123 Le Loi, HCMC", "category": "Shoes", "product_info": "Running shoes size 40-45", "promotion": "10% off running shoes", "latitude": 10.77, "longitude": 106.69},
        {"store_id": "2", "store_name": "Shop B", "address": "456 Nguyen Hue, HCMC", "category": "Electronics", "product_info": "Latest iPhones and Androids", "promotion": "Free screen protector with any phone", "latitude": 10.765, "longitude": 106.685},
        {"store_id": "3", "store_name": "Shop C", "address": "789 Tran Hung Dao, HCMC", "category": "Apparel", "product_info": "T-shirts, jeans, dresses", "promotion": "Buy 2 get 1 free on t-shirts", "latitude": 10.768, "longitude": 106.675}
    ]
    stores_df_test = pd.DataFrame(data)

    user_lat_test = 10.762622  # User's current latitude
    user_long_test = 106.660172 # User's current longitude

    nearest = find_nearest_store(user_lat_test, user_long_test, stores_df_test)
    if nearest:
        print(f"Nearest store: {nearest['store_name']} at {nearest['address']} ({nearest['distance_km']:.2f} km away)")
    else:
        print("No stores found.")
