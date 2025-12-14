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
    
    # Handle location requests separately
    if is_location_request:
        print("User requested location check.")
        # Return empty stores, frontend will handle location prompt
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
                        price=str(row.get('Giá bán', 'Liên hệ')),
                        image_url=str(row.get('Link ảnh', '')),
                        link=str(row.get('Link sản phẩm', ''))
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
                from services.geo_service import calculate_distance
                distance = calculate_distance(
                    user_latitude, user_longitude,
                    shop['latitude'], shop['longitude']
                )
                
                shops_with_distance.append({
                    'shop': shop,
                    'distance': distance,
                    'product_name': product_name
                })
            
            # Sort by distance
            shops_with_distance.sort(key=lambda x: x['distance'])
            
            if not shops_with_distance:
                raise ValueError("No valid shops found for selected products")
            
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
                price = str(product_row['Giá bán'].iloc[0]) if pd.notna(product_row['Giá bán'].iloc[0]) else "Liên hệ"
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
            
            # Build response with all shops
            nearest_stores_response = []
            for item in shops_with_distance[:5]:  # Top 5 shops
                shop = item['shop']
                
                # Get products for this shop
                shop_products_df = category_products_df[
                    category_products_df['ID Shop'].astype(str) == str(shop['store_id'])
                ]
                
                matching_products = []
                for _, row in shop_products_df.head(5).iterrows():
                    matching_products.append(ProductInfo(
                        name=str(row.get('Tên sản phẩm', 'Sản phẩm')),
                        price=str(row.get('Giá bán', 'Liên hệ')),
                        image_url=str(row.get('Link ảnh', '')),
                        link=str(row.get('Link sản phẩm', ''))
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
                            price=str(row.get('Giá bán', 'Liên hệ')),
                            image_url=str(row.get('Link ảnh', '')),
                            link=str(row.get('Link sản phẩm', ''))
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
