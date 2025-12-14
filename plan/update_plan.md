# Implementation Plan: AI-Powered Product Search v2.0

## 🎯 Objective
Optimize the product search system by:
1. Reducing AI calls from **3 → 2** (or **2 → 1** with fallback)
2. Improving accuracy through AI semantic understanding
3. Using **Template + Placeholder** pattern for natural responses with accurate data

---

## 🔄 New Workflow

```
User Query 
  ↓
[AI Call #1] Extract Intent → {category, product_name, generic_term}
  ↓
[System] Filter products from category sheet (2 columns: Tên SP, Tên Shop)
  ↓
[AI Call #2] Smart Filter + Generate Template → {found, products[], ai_message_template}
  ↓
[System] Calculate distance, fetch details, replace placeholders
  ↓
[Output] Final response to User
```

---

## 📊 Technical Changes

### 1. Data Sent to AI Call #2
**Only 2 columns from category sheet:**
- `Tên sản phẩm` (Product Name)
- `Tên Shop` (Shop Name)

**NOT sent:** Link ảnh, Giá, Địa chỉ (System will fill these via placeholders)

---

### 2. Standard Placeholders

| Placeholder | Data Source |
|-------------|-------------|
| `{{product_name}}` | AI selects from data |
| `{{shop_name}}` | AI selects from data |
| `{{distance}}` | System calculates |
| `{{address}}` | System fetches from `stores_dataframe` |
| `{{price}}` | System fetches from `products_dataframe` |
| `{{image_url}}` | System fetches from `products_dataframe` |
| `{{zalo_link}}` | System fetches from `stores_dataframe` |

---

### 3. AI Call #2 Response Format

```json
{
  "found": true,
  "products": [
    {"product_name": "Đồ chơi ABC", "shop_name": "Shop Tình Yêu"}
  ],
  "ai_message_template": "Dạ em tìm thấy {{product_name}} tại {{shop_name}}, cách anh {{distance}} km ({{address}}). Giá {{price}}, xem hình tại {{image_url}} ạ!"
}
```

---

## 🔄 Complete Fallback Strategy

### Case 1: AI Call #1 Returns NO Category (`category == null`)

**Action:**
1. Regex search across **ALL products** in `products_dataframe`
2. Get top 3 matches
3. **If found (> 0):**
   - Fetch shop info
   - Calculate distance
   - Call AI #3 to generate formatted response
4. **If NOT found (= 0):**
   - Return fixed message:
   ```
   "Rất tiếc, em không tìm thấy sản phẩm phù hợp với yêu cầu của anh/chị. 
    Anh/chị có thể thử tìm kiếm sản phẩm khác hoặc mô tả chi tiết hơn không ạ?"
   ```

---

### Case 2: AI Call #2 Returns `found: false`

**Action:**
→ **Same as Case 1:**
1. Regex search all products
2. Top 3 matches
3. If found → AI Call #3
4. If not found → Fixed message

---

### Case 3: AI Call #2 Error (Invalid Format / Quota Exceeded / Timeout)

**Action:**
1. **Log error to system:**
   ```python
   print(f"ERROR: AI Call #2 failed - {error_details}")
   logging.error(f"AI Call #2 error: {e}")
   ```

2. **Return to user:**
   ```
   "Xin lỗi anh/chị, hệ thống đang gặp sự cố kết nối. 
    Vui lòng thử lại sau ít phút hoặc liên hệ bộ phận hỗ trợ ạ!"
   ```

3. **DO NOT fallback** to regex (to avoid incorrect results when system is unstable)

---

## 📁 Files to Modify

### 1. `backend-app/services/ai_service.py`

#### Add New Function: `smart_product_filter()`

**Purpose:** AI Call #2 - Smart product filtering with template generation

**Input:**
```python
async def smart_product_filter(user_query: str, category_products: list) -> dict:
    """
    Args:
        user_query: User's search query
        category_products: List of {"product_name": "...", "shop_name": "..."}
    
    Returns:
        {
            "found": bool,
            "products": [{"product_name": "...", "shop_name": "..."}],
            "ai_message_template": str
        }
    """
```

**Prompt Template:**
```
Nhiệm vụ: Tìm sản phẩm khớp với "{user_query}" trong danh sách.

Danh sách sản phẩm:
{category_products}

Yêu cầu:
1. Trả về JSON: {"found": true/false, "products": [...], "ai_message_template": "..."}
2. Template có thể dùng các placeholder sau (hệ thống sẽ tự bù):
   - {{product_name}}: Tên sản phẩm
   - {{shop_name}}: Tên shop
   - {{distance}}: Khoảng cách (km)
   - {{address}}: Địa chỉ shop
   - {{price}}: Giá sản phẩm
   - {{image_url}}: Link ảnh sản phẩm
   - {{zalo_link}}: Link Zalo shop
3. NẾU không tìm thấy: "found": false
4. Template phải tự nhiên, thân thiện, phù hợp ngữ cảnh Việt Nam
5. KHÔNG tự sáng tạo tên sản phẩm/shop, chỉ dùng từ danh sách
```

---

### 2. `backend-app/main.py`

#### Modify `/chat` Endpoint Logic:

```python
@app.post("/chat", response_model=ChatResponse)
async def chat_with_ai(request: ChatRequest):
    # Step 1: AI Call #1 - Extract Intent (UNCHANGED)
    search_intent = await extract_search_intent(user_message, unique_categories)
    
    # Step 2: Check if category exists
    if not search_intent or not search_intent.get('category'):
        # FALLBACK CASE 1: No category
        matched_products = regex_search_all_products(user_message)
        if len(matched_products) > 0:
            # Found products → AI Call #3
            ai_reply = await get_ai_response(...)
            return ChatResponse(reply=ai_reply, ...)
        else:
            # No products found
            return ChatResponse(
                reply="Rất tiếc, em không tìm thấy sản phẩm phù hợp...",
                nearest_stores=[]
            )
    
    # Step 3: Filter products by category
    category_name = search_intent['category']
    category_products_df = products_dataframe[
        products_dataframe['Danh mục'].str.contains(category_name, case=False, na=False)
    ]
    
    # Prepare data for AI (only 2 columns)
    category_products = []
    for _, row in category_products_df.iterrows():
        shop_id = row['ID Shop']
        shop_name = stores_dataframe[
            stores_dataframe['store_id'] == str(shop_id)
        ]['store_name'].iloc[0] if not stores_dataframe[
            stores_dataframe['store_id'] == str(shop_id)
        ].empty else "Unknown"
        
        category_products.append({
            "product_name": row['Tên sản phẩm'],
            "shop_name": shop_name
        })
    
    # Limit to 200 products max (to avoid token overflow)
    category_products = category_products[:200]
    
    # Step 4: AI Call #2 - Smart Filter
    try:
        ai_result = await smart_product_filter(user_message, category_products)
        
        if ai_result['found']:
            # SUCCESS PATH: Replace placeholders
            selected_products = ai_result['products']
            
            # Get shop details and calculate distance
            shops_with_distance = []
            for prod in selected_products:
                shop_name = prod['shop_name']
                shop_row = stores_dataframe[
                    stores_dataframe['store_name'] == shop_name
                ]
                if not shop_row.empty:
                    shop = shop_row.iloc[0]
                    distance = calculate_distance(
                        user_latitude, user_longitude,
                        shop['latitude'], shop['longitude']
                    )
                    shops_with_distance.append({
                        'shop': shop,
                        'distance': distance,
                        'product_name': prod['product_name']
                    })
            
            # Sort by distance
            shops_with_distance.sort(key=lambda x: x['distance'])
            
            # Replace placeholders in template
            if shops_with_distance:
                nearest = shops_with_distance[0]
                shop = nearest['shop']
                
                # Fetch product details
                product_row = products_dataframe[
                    (products_dataframe['Tên sản phẩm'] == nearest['product_name']) &
                    (products_dataframe['ID Shop'] == shop['store_id'])
                ]
                
                price = product_row['Giá bán'].iloc[0] if not product_row.empty else "Liên hệ"
                image_url = product_row['Link ảnh'].iloc[0] if not product_row.empty else ""
                
                # Replace placeholders
                final_message = ai_result['ai_message_template']
                final_message = final_message.replace("{{product_name}}", nearest['product_name'])
                final_message = final_message.replace("{{shop_name}}", shop['store_name'])
                final_message = final_message.replace("{{distance}}", f"{nearest['distance']:.1f}")
                final_message = final_message.replace("{{address}}", shop['address'])
                final_message = final_message.replace("{{price}}", str(price))
                final_message = final_message.replace("{{image_url}}", str(image_url))
                final_message = final_message.replace("{{zalo_link}}", shop.get('zalo_group_link', ''))
                
                # Build response
                nearest_stores_response = [...]  # Build StoreInfo objects
                
                return ChatResponse(
                    reply=final_message,
                    nearest_stores=nearest_stores_response
                )
        else:
            # FALLBACK CASE 2: AI found nothing
            matched_products = regex_search_all_products(user_message)
            if len(matched_products) > 0:
                ai_reply = await get_ai_response(...)  # AI Call #3
                return ChatResponse(reply=ai_reply, ...)
            else:
                return ChatResponse(
                    reply="Rất tiếc, em không tìm thấy sản phẩm phù hợp...",
                    nearest_stores=[]
                )
    
    except Exception as e:
        # FALLBACK CASE 3: AI Call #2 error
        print(f"ERROR: AI Call #2 failed - {str(e)}")
        logging.error(f"AI Call #2 error: {e}")
        return ChatResponse(
            reply="Xin lỗi anh/chị, hệ thống đang gặp sự cố kết nối. Vui lòng thử lại sau ít phút ạ!",
            nearest_stores=[]
        )
```

#### Add Helper Function: `regex_search_all_products()`

```python
def regex_search_all_products(query: str, limit: int = 3) -> pd.DataFrame:
    """
    Search across all products using regex
    
    Args:
        query: Search query
        limit: Max results to return
    
    Returns:
        DataFrame of matched products
    """
    search_terms = query.split()
    mask = pd.Series([True] * len(products_dataframe))
    
    for term in search_terms:
        term_mask = products_dataframe['Tên sản phẩm'].str.contains(
            term, case=False, na=False
        )
        mask = mask & term_mask
    
    return products_dataframe[mask].head(limit)
```

---

## 🧪 Testing Plan

### Test Cases:

1. **Happy Path:**
   - Query: "đồ chơi người lớn"
   - Expected: AI Call #2 finds products → Template with placeholders → Success

2. **Typo Handling:**
   - Query: "đồ chơi ngườil lớn"
   - Expected: AI Call #1 fixes typo → AI Call #2 finds products

3. **No Category:**
   - Query: "sản phẩm xyz không tồn tại"
   - Expected: AI Call #1 returns no category → Regex all products → Fixed message

4. **AI Call #2 Finds Nothing:**
   - Query: "sản phẩm rất cụ thể không có"
   - Expected: AI Call #2 returns `found: false` → Regex fallback → AI Call #3 or fixed message

5. **AI Call #2 Error:**
   - Simulate quota exceeded
   - Expected: Error logged → User sees "Hệ thống lỗi" message

---

## ⚠️ Important Notes

1. **Token Limit:** Limit category products to 200 items max to avoid token overflow
2. **Validation:** Validate AI Call #2 response format before processing
3. **Logging:** Log all AI errors for debugging
4. **Fallback Template:** Use default template if AI returns invalid one
5. **No Git Commit:** Changes will NOT be committed to git per user request

---

## ✅ Success Criteria

- [ ] AI Call #2 function implemented and working
- [ ] Placeholder replacement logic working correctly
- [ ] All 3 fallback cases handled properly
- [ ] Error messages user-friendly
- [ ] System logs errors appropriately
- [ ] Testing completed for all scenarios
