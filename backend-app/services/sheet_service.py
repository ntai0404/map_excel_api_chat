import pandas as pd
import os
import sys

# Import from geo_service
from services.geo_service import geocode_address, build_address, load_cache

# Google Sheets Configuration
SPREADSHEET_ID = "1ekdjU2lJK1MnBzwFr3B8ws2E8GnK1omLJNbIU8puXPI"

# All sheet GIDs (product categories)
SHEET_GIDS = {
    "815593620": "Balo - Túi xách - Vali",
    "1986607723": "Bàn , ghế",
    "871059786": "Bàn chải & Tăm nước",
    "28491151": "Bàn phím & Chuột",
    "1752922142": "Bình nước nóng",
    "2127097084": "Bếp từ , bếp điện",
    "1436681271": "Chăm sóc nhà cửa",
    "444196920": "Củ cáp sạc",
    "667498198": "Dịch vụ , phần mềm online…",
    "1643965690": "Dụng cụ cầm tay , máy khoan , cắt…",
    "1258563817": "Dụng cụ nhà bếp",
    "866725333": "Dụng cụ thể thao",
    "397341247": "Kính mắt",
    "281899121": "Loa",
    "1949182727": "Ly, cốc, bình giữ nhiệt",
    "478019717": "Máy chiếu",
    "148397415": "Máy chơi game",
    "801472824": "Máy hút ẩm , tạo ẩm , phun sương",
    "1081652131": "Máy lọc không khí",
    "374890050": "Máy Massage",
    "2137820275": "Máy tính & Laptop",
    "824530554": "Máy xay - Máy ép",
    "1175290915": "Máy ảnh & Camera",
    "333396090": "Mũ nón",
    "1877546024": "Mẹ và Bé",
    "379520387": "Nhà cửa & đời sống",
    "1688160677": "Nội thất",
    "835156817": "Phòng ngủ",
    "805437056": "Phụ kiện khác",
    "764742527": "Phụ tùng",
    "1861521418": "Pin,Sạc dự phòng , ắc quy",
    "1950842517": "Quần áo",
    "1076652714": "Robot & Máy hút bụi , lau nhà",
    "1067024040": "Sức khỏe & làm đẹp",
    "1420423361": "Tai nghe - Micro",
    "634047726": "Thiết bị - Phụ kiện",
    "1758622918": "Thiết bị khác",
    "31506967": "Thiết bị âm thanh",
    "1673898824": "Thiết bị điện gia dụng",
    "1477558516": "Thùng các tông",
    "951706041": "Thời trang",
    "276874696": "Thực phẩm & Đồ ăn",
    "1690410600": "Tivi ; máy chiếu",
    "124067928": "Trang sức",
    "1722661331": "Trang trí nhà cửa",
    "1714524348": "Văn phòng phẩm",
    "654519370": "Vỏ ốp lưng & miếng dán",
    "301554865": "Vợt muỗi , đèn bắt muỗi",
    "839522919": "Xốp , bọt , cột khí",
    "608057419": "Ô tô - Xe máy - Xe đạp",
    "183193452": "Điều hòa - Quạt",
    "142217162": "Điện thoại & phụ kiện",
    "1565181241": "Điện thoại",
    "111911700": "Đèn & ánh sáng",
    "156635143": "Đồ Camping , phượt , cắm trại",
    "671032773": "Đồ chơi - Phụ kiện",
    "1180757598": "Đồ chơi người lớn , phòng the",
    "1028300741": "Đồ chơi",
    "1970437403": "Đồ dùng khác",
    "1984447125": "Đồ dùng nhà tắm",
    "1852736408": "Đồ phong thuỷ , tâm linh",
    "838564855": "Đồng hồ",
}

def load_all_products():
    """Load products from all sheets"""
    print(f"📥 Loading products from {len(SHEET_GIDS)} sheets...")
    
    all_products = []
    
    for gid, category_name in SHEET_GIDS.items():
        try:
            csv_url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid={gid}"
            df = pd.read_csv(csv_url)
            
            # Add category if not exists
            if 'Danh mục' not in df.columns:
                df['Danh mục'] = category_name
            
            all_products.append(df)
            print(f"  ✓ {category_name}: {len(df)} products")
            
        except Exception as e:
            print(f"  ✗ {category_name}: Error - {e}")
    
    if all_products:
        combined_df = pd.concat(all_products, ignore_index=True)
        print(f"\n✅ Total products loaded: {len(combined_df)}")
        return combined_df
    else:
        print("\n❌ No products loaded")
        return pd.DataFrame()

def aggregate_shops(products_df):
    """Aggregate products by shop"""
    print(f"\n🏪 Aggregating products by shop...")
    
    # Group by shop ID
    shop_groups = products_df.groupby('ID Shop')
    
    shops = []
    geocode_cache = load_cache()
    
    for shop_id, group in shop_groups:
        # Get shop info from first product
        first_product = group.iloc[0]
        
        # Extract unique categories
        categories = group['Danh mục'].dropna().unique().tolist()
        
        # Build address from 3 columns
        ward = first_product.get('Phường/Xã', '')
        district = first_product.get('Quận/Huyện', '')
        city = first_product.get('Tỉnh/TP', '')
        
        address = build_address(ward, district, city)
        
        # Geocode address
        coords = geocode_address(address, geocode_cache)
        
        if coords:
            lat, lng = coords
        else:
            # Fallback to center of Vietnam
            lat, lng = 16.0544, 108.2022
        
        # Try to find 'Link Zalo' column with case-insensitive search
        zalo_link = ''
        for col in first_product.index:
            if str(col).strip().lower() == 'link zalo':
                val = first_product[col]
                if pd.notna(val):
                    zalo_link = str(val).strip()
                break
        
        # Create a searchable string of product names (top 20)
        product_names = group['Tên sản phẩm'].dropna().unique().tolist()
        searchable_products = " | ".join(map(str, product_names[:20]))
        
        shop = {
            'store_id': str(shop_id),
            'store_name': first_product['Tên Shop'],
            'address': address,
            'city': city,
            'district': district,
            'ward': ward,
            'shop_type': first_product.get('Loại Shop', ''),
            'product_count': len(group),
            'zalo_group_link': zalo_link,
            'categories': ', '.join(categories),
            'category': categories[0] if categories else '',  # For compatibility
            'latitude': lat,
            'longitude': lng,
            # CRITICAL FIX: Include product names in product_info for search filtering
            'product_info': searchable_products if searchable_products else f"{len(group)} sản phẩm",
            'promotion': ''  # Can be added later
        }
        
        shops.append(shop)
    
    shops_df = pd.DataFrame(shops)
    print(f"✅ Aggregated {len(shops_df)} unique shops")
    
    return shops_df

def load_stores_data():
    """Main function to load and process store data"""
    print("\n" + "=" * 80)
    print("LOADING STORE DATA FROM NEW GOOGLE SHEETS")
    print("=" * 80)
    
    # Load all products
    products_df = load_all_products()
    
    if products_df.empty:
        print("❌ No data loaded")
        return pd.DataFrame(), pd.DataFrame()
    
    # Aggregate into shops
    shops_df = aggregate_shops(products_df)
    
    print("\n" + "=" * 80)
    print(f"✅ DATA LOADED SUCCESSFULLY: {len(shops_df)} shops")
    print("=" * 80)
    
    return shops_df, products_df

if __name__ == '__main__':
    # Test loading
    store_df = load_stores_data()
    if not store_df.empty:
        print("\nSample data:")
        print(store_df.head())
        print(f"\nColumns: {list(store_df.columns)}")
