// DUAL ACTION: Join Group + Chat with Admin/Staff
// Global function to be accessible by onclick handlers
function handleDualZaloAction(groupLink, productName, staffZalo) {
    // 1. Prepare Admin Chat Link (Deep Link)
    // If staffZalo is provided (from Link NV), use it. Otherwise placeholder or skip.
    // If staffZalo is missing or invalid, we prioritize Group Link only.

    let adminChatLink = "";

    if (staffZalo && staffZalo.length > 8) {
        const msg = encodeURIComponent(`Chào bạn, tôi quan tâm sản phẩm: ${productName}. Nhờ hỗ trợ!`);
        adminChatLink = `https://zalo.me/${staffZalo}?text=${msg}`;
    }

    // DEBUG: Log to Console only (User Request)
    console.log("Dual Action Debug:", { groupLink, staffZalo, adminChatLink });

    // SEQUENCING FOR UX (User Verified):
    // 1. Open Group Link (Background Context)
    const win1 = window.open(groupLink, '_blank');

    // 2. Open Staff Chat (Foreground Action)
    if (adminChatLink) {
        // Try opening second tab
        const win2 = window.open(adminChatLink, '_blank');

        if (!win2 || win2.closed || typeof win2.closed == 'undefined') {
            renderMessage('ai', '⚠️ <b>LỖI CHẶN POP-UP!</b><br>Máy tính đã chặn cửa sổ Chat Nhân Viên. Vui lòng bấm vào icon [Pop-up] trên thanh địa chỉ và chọn "Always Allow" (Luôn cho phép).', true);
        } else {
            console.log("Dual Action: Group -> Staff Chat (Success)");
        }
    } else {
        renderMessage('ai', '⚠️ <b>LỖI DỮ LIỆU:</b> Không tìm thấy số Zalo nhân viên (Link NV).', true);
    }
}

let map;
let userMarker;
let storeMarkers = L.featureGroup();
let currentUserLocation = null;
let chatHistory = []; // Global history array
window.lastSearchTime = Date.now(); // Global context timer
window.interestedProducts = JSON.parse(localStorage.getItem('interestedProducts') || '[]'); // Accumulate products user is interested in
function saveInterestedProducts() {
    localStorage.setItem('interestedProducts', JSON.stringify(window.interestedProducts));
}

// Icons configuration (Global to avoid re-creation and ensures CDN priority)
const redIcon = L.icon({
    iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-red.png',
    shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png',
    iconSize: [25, 41],
    iconAnchor: [12, 41],
    popupAnchor: [1, -34],
    shadowSize: [41, 41]
});

const blueIcon = L.icon({
    iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-blue.png',
    shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png',
    iconSize: [25, 41],
    iconAnchor: [12, 41],
    popupAnchor: [1, -34],
    shadowSize: [41, 41]
});

// Configure Markdown renderer safely
if (typeof marked !== 'undefined') {
    const renderer = new marked.Renderer();
    renderer.link = function (href, title, text) {
        // Prevent undefined hrefs if possible, though strictness is good
        if (!href || href === 'undefined' || href === 'null') href = '#';
        return `<a href="${href}" title="${title || ''}" target="_self">${text}</a>`;
    };
    marked.setOptions({ renderer: renderer });
}

// --- Chat History Persistence ---
function getStorage() {
    // We use sessionStorage for all users' chat history to ensure privacy on shared devices.
    // This persists during same-tab navigation but clears when the tab is closed.
    return sessionStorage;
}

function getHistoryKey() {
    const sessionId = localStorage.getItem('session_id') || 'guest';
    return `chat_history_${sessionId}`;
}

function saveHistory() {
    const storage = getStorage();
    storage.setItem(getHistoryKey(), JSON.stringify(chatHistory));
}

function loadHistory() {
    const storage = getStorage();
    const saved = storage.getItem(getHistoryKey());
    if (saved) {
        try {
            chatHistory = JSON.parse(saved);
            chatHistory.forEach(item => {
                if (item.type === 'message') {
                    renderMessage(item.sender, item.text, false);
                } else if (item.type === 'stores') {
                    renderStoreCards(item.data, false);
                }
            });
        } catch (e) {
            console.error("Error loading history:", e);
            chatHistory = [];
        }
    }
}

// Inject CSS for Store Cards
const style = document.createElement('style');
style.innerHTML = `
    .store-list {
        margin-top: 10px;
        display: flex;
        flex-direction: column;
        gap: 10px;
    }
    .store-card {
        background: #fff;
        border: 1px solid #ddd;
        border-radius: 8px;
        padding: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        font-size: 0.9em;
    }
    .store-name {
        font-weight: bold;
        color: #007bff;
        margin-bottom: 4px;
    }
    .store-address {
        color: #555;
        font-size: 0.85em;
    }
    .store-address {
        color: #555;
        font-size: 0.85em;
    }
    .zalo-btn {
        display: inline-block;
        margin-top: 5px;
        padding: 5px 10px;
        background-color: #0068ff;
        color: white;
        text-decoration: none;
        border-radius: 4px;
        font-size: 0.85em;
    }
    .zalo-btn:hover {
        background-color: #0054cc;
        color: white;
    }
    .product-list {
        display: flex;
        overflow-x: auto;
        gap: 10px;
        margin-top: 10px;
        padding-bottom: 5px;
        border-top: 1px solid #eee;
        padding-top: 10px;
    }
    .product-item {
        min-width: 120px;
        max-width: 120px;
        border: 1px solid #eee;
        border-radius: 6px;
        overflow: hidden;
        font-size: 0.8em;
    }
    .product-img {
        width: 100%;
        height: 80px;
        object-fit: cover;
    }
    .product-info {
        padding: 5px;
    }
    .product-name {
        font-weight: bold;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        color: #333;
    }
    .product-price {
        color: #d9534f;
        font-weight: bold;
    }
    .product-link-btn {
        display: inline-block;
        margin-top: 4px;
        padding: 3px 8px;
        background-color: #28a745;
        color: white;
        text-decoration: none;
        border-radius: 3px;
        font-size: 0.75em;
        text-align: center;
        transition: all 0.2s ease;
    }
    .product-link-btn:hover {
        background-color: #218838;
        color: white;
        transform: scale(1.05);
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    }
`;
document.head.appendChild(style);

// 3.1. Khởi tạo Bản đồ (Map Initialization)
function initializeMap() {
    map = L.map('map-container').setView([10.762622, 106.660172], 13); // Default to a general location in Vietnam (e.g., HCMC)

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);

    storeMarkers.addTo(map);

    // Fix for Leaflet images not loading from absolute paths (prevents 404 spinning)
    L.Icon.Default.imagePath = 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/';
}

function updateMap(userLat, userLng, stores) {
    if (userMarker) {
        map.removeLayer(userMarker);
    }

    if (userLat && userLng) {
        userMarker = L.marker([userLat, userLng], { icon: redIcon }).addTo(map)
            .bindPopup('You are here').openPopup();
        map.setView([userLat, userLng], 13);
    }

    // Only update stores if a new list is provided (not null)
    if (stores !== null) {
        storeMarkers.clearLayers();
        if (stores.length > 0) {
            stores.forEach(store => {
                const zaloLink = store.zalo_group_link ?
                    `<br><a href="${store.zalo_group_link}" target="_blank" class="zalo-btn" style="margin-top: 8px;">💬 Tham gia nhóm Zalo</a>` : '';

                L.marker([store.lat, store.lng], { icon: blueIcon })
                    .addTo(storeMarkers)
                    .bindPopup(`<b>${store.name}</b><br>${store.description || ''}${zaloLink}`).openPopup();
            });
        }
    }

    // Fit bounds logic: Use new stores if provided, otherwise simply maintain view or fit to user + existing
    // Note: If we just updated location, we might want to keep existing markers in view if possible, 
    // but the original logic was to fit bounds if stores were provided.

    if (stores && stores.length > 0) {
        if (userLat && userLng) {
            const bounds = new L.LatLngBounds();
            bounds.extend([userLat, userLng]);
            stores.forEach(store => bounds.extend([store.lat, store.lng]));
            map.fitBounds(bounds, { padding: [50, 50] });
        } else {
        }
    }
}

// --- Geolocation Logic ---
let isLocating = false;

function getUserLocation() {
    if (isLocating) {
        console.log("GPS: Request already in progress, waiting...");
        return new Promise((resolve) => {
            const check = setInterval(() => {
                if (!isLocating) {
                    clearInterval(check);
                    resolve(currentUserLocation || null);
                }
            }, 500);
        });
    }

    return new Promise((resolve) => {
        if (!navigator.geolocation) {
            console.warn("GPS: Geolocation not supported.");
            resolve(null);
            return;
        }

        isLocating = true;

        // Browser options: 30s timeout, use 5-min cache if available
        const options = {
            enableHighAccuracy: false,
            timeout: 30000,
            maximumAge: 300000
        };

        navigator.geolocation.getCurrentPosition(
            (position) => {
                isLocating = false;
                currentUserLocation = {
                    lat: position.coords.latitude,
                    lng: position.coords.longitude
                };
                console.log("GPS: Success!", currentUserLocation);
                sessionStorage.setItem('last_location', JSON.stringify(currentUserLocation));
                updateMap(currentUserLocation.lat, currentUserLocation.lng, null);
                resolve(currentUserLocation);
            },
            (error) => {
                isLocating = false;
                console.warn("GPS: Failed with error code:", error.code, error.message);
                // Return cached location if valid, else null
                resolve(currentUserLocation || null);
            },
            options
        );
    });
}

// 3.3. Kết nối Backend (Real API Call)
async function fetchAIResponse(userMessage, userLocation) {
    try {
        const response = await fetch('/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                message: userMessage,
                latitude: userLocation ? userLocation.lat : 0.0,
                longitude: userLocation ? userLocation.lng : 0.0
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        // Map backend response format to frontend format
        // Backend returns: { reply: "...", nearest_stores: [ { ... }, ... ] }
        let stores = [];
        if (data.nearest_stores && data.nearest_stores.length > 0) {
            data.nearest_stores.forEach(store => {
                stores.push({
                    name: store.name,
                    lat: store.lat,
                    lng: store.lng,
                    description: store.address,
                    distance_km: store.distance_km,  // Add distance
                    zalo_group_link: store.zalo_group_link,
                    products: store.products || [],
                    staff_zalo: store.staff_zalo || '' // Add staff Zalo ID
                });
            });
        }

        return {
            text: data.reply,
            map_data: {
                user_marker: userLocation,
                store_markers: stores
            },
            trigger_location: data.trigger_location
        };

    } catch (error) {
        console.error("Error fetching AI response:", error);
        return {
            text: "Xin lỗi, tôi không thể kết nối với máy chủ lúc này. Vui lòng thử lại sau.",
            map_data: null
        };
    }
}

// 3.4. Xử lý Chat (UI Interaction)
const chatMessages = document.getElementById('chat-messages');
const chatInput = document.getElementById('chat-input');
const sendButton = document.getElementById('send-button');
const locationButton = document.getElementById('location-button');

function appendMessage(sender, text) {
    return renderMessage(sender, text, true);
}

function renderMessage(sender, text, save = true) {
    const messageElement = document.createElement('div');
    messageElement.classList.add('message', sender);

    // Parse Markdown for AI messages, keep plain text for user
    const content = sender === 'ai' ? marked.parse(text) : text;

    messageElement.innerHTML = `<div class="message-bubble">${content}</div>`;
    chatMessages.appendChild(messageElement);
    chatMessages.scrollTop = chatMessages.scrollHeight; // Auto-scroll to bottom

    // DON'T save temporary typing indicators to history
    if (save && !text.includes('typing-indicator')) {
        chatHistory.push({ type: 'message', sender, text });
        saveHistory();
    }
    return messageElement;
}

async function sendMessage() {
    const userMessage = chatInput.value.trim();
    if (userMessage === '') return;

    appendMessage('user', userMessage);
    chatInput.value = '';

    const typingIndicator = renderMessage('ai', '<div class="typing-indicator">AI is typing...</div>', false); // Don't save this

    // Use cached location if available to prevent repeated prompts
    const location = currentUserLocation || await getUserLocation();

    const aiResponse = await fetchAIResponse(userMessage, location);

    // Remove typing indicator
    if (typingIndicator) {
        typingIndicator.remove();
    }

    if (aiResponse && !aiResponse.trigger_location) {
        appendMessage('ai', aiResponse.text);
    }

    // Render Store Cards
    if (aiResponse.map_data && aiResponse.map_data.store_markers && aiResponse.map_data.store_markers.length > 0) {
        renderStoreCards(aiResponse.map_data.store_markers, true);
    }

    // Auto-trigger location if backend requested it
    if (aiResponse.trigger_location) {
        console.log("Backend requested location trigger.");
        handleLocationCheck(true);
    }
}

function clearHistory() {
    chatHistory = [];
    localStorage.removeItem(getHistoryKey());
    sessionStorage.removeItem(getHistoryKey());
}

function renderStoreCards(stores, save = true) {
    const storeListHtml = document.createElement('div');
    storeListHtml.className = 'store-list';

    // UPDATE CONTEXT TIMER
    window.lastSearchTime = Date.now();

    stores.forEach(store => {
        const card = document.createElement('div');
        card.className = 'store-card';
        card.onclick = () => focusOnStore(store.lat, store.lng, store.name);
        card.style.cursor = 'pointer';

        // Use first product name from filtered results
        const interestName = (store.products && store.products.length > 0) ? store.products[0].name : store.name;

        card.innerHTML = `
            <div class="store-name">${store.name}</div>
            <div class="store-address">${store.description || store.address || ''}</div>
            <div class="store-distance">📏 Cách bạn: ${store.distance_km ? store.distance_km.toFixed(1) : '?'} km</div>
            
            ${store.products && store.products.length > 0 ? `
                <div class="product-list">
                    ${store.products.map((p, index) => {
            let finalLink = p.link || '#';
            if (store.zalo_group_link && finalLink !== '#') {
                const separator = finalLink.includes('?') ? '&' : '?';
                finalLink += `${separator}zalo=${encodeURIComponent(store.zalo_group_link)}&product_name=${encodeURIComponent(p.name)}`;
            } else if (finalLink !== '#') {
                const separator = finalLink.includes('?') ? '&' : '?';
                finalLink += `${separator}product_name=${encodeURIComponent(p.name)}`;
            }

            const isHidden = index >= 3 ? 'display:none;' : '';
            const hiddenClass = index >= 3 ? 'hidden-product' : '';

            return `
                        <div class="product-item ${hiddenClass}" style="${isHidden}">
                            <img src="${p.image_url || 'https://via.placeholder.com/120'}" class="product-img" onerror="this.src='https://via.placeholder.com/120?text=No+Image'">
                            <div class="product-info">
                                <div class="product-name" title="${p.name}">${p.name}</div>
                                <div class="product-price">${p.price}</div>
                                <a href="${finalLink}" target="_self" class="product-link-btn" onclick="event.stopPropagation()">🔗 Xem sản phẩm</a>
                            </div>
                        </div>`;
        }).join('')}
                    
                    ${store.products.length > 3 ?
                    `<button class="see-more-btn" style="width:100%; margin-top:5px; padding:5px; background:#f0f0f0; border:1px solid #ddd; cursor:pointer;" onclick="revealNextBatch(this)">Xem thêm (${store.products.length - 3} sản phẩm)</button>`
                    : ''}
                </div>
            ` : ''}

            ${store.zalo_group_link ?
                `<br><a href="${store.zalo_group_link}" target="_blank" class="zalo-btn" style="display:inline-block; text-decoration:none; text-align:center;" onclick="trackInterest(event, '${safeEncode(store.name)}', '${safeEncode(store.zalo_group_link)}', '${safeEncode(interestName)}')">📢 Tham gia nhóm săn sale</a>`
                : ''}
        `;
        storeListHtml.appendChild(card);
    });
    chatMessages.appendChild(storeListHtml);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    // Update map markers (Keep user marker if exists)
    const lat = currentUserLocation ? currentUserLocation.lat : null;
    const lng = currentUserLocation ? currentUserLocation.lng : null;
    updateMap(lat, lng, stores);

    if (save) {
        chatHistory.push({ type: 'stores', data: stores });
        saveHistory();
    }
}

// Function to focus map on a specific store
function focusOnStore(lat, lng, name) {
    if (map) {
        map.setView([lat, lng], 16); // Zoom in closer

        // Find and open the popup for this store
        storeMarkers.eachLayer(function (layer) {
            if (layer.getLatLng().lat === lat && layer.getLatLng().lng === lng) {
                layer.openPopup();
            }
        });
    }
}

sendButton.addEventListener('click', sendMessage);
chatInput.addEventListener('keypress', function (e) {
    if (e.key === 'Enter') {
        sendMessage();
    }
});

// --- 3.5. Xử lý logic lấy vị trí (Refactored - Silent UI) ---
async function handleLocationCheck(isAutoTriggered = false) {
    if (isLocating) return;

    // UI Feedback on button
    const locBtnIcon = locationButton.querySelector('i');
    if (locBtnIcon) locBtnIcon.className = 'fas fa-spinner fa-spin';
    locationButton.disabled = true;

    try {
        const location = await getUserLocation();

        if (location) {
            // Updated logic: ALWAYS silent for auto-trigger (as requested by user)
            // Manual click (!isAutoTriggered) still shows feedback
            if (!isAutoTriggered) {
                renderMessage('ai', `Đã xác định được vị trí của bạn: Lat ${location.lat}, Lng ${location.lng}.Tôi có thể giúp bạn tìm gì gần đây ? `, true);
            }
            // Still mark resolved so we don't nag
            sessionStorage.setItem('locationResolved', 'true');
        } else if (!isAutoTriggered) {
            renderMessage('ai', 'Không thể lấy vị trí. Vui lòng kiểm tra cài đặt trình duyệt và thử lại.', true);
        }
    } catch (err) {
        console.error("Location error:", err);
    } finally {
        if (locBtnIcon) locBtnIcon.className = 'fas fa-map-marker-alt';
        locationButton.disabled = false;
    }
}

locationButton.addEventListener('click', () => {
    renderMessage('user', 'Vị trí của tôi', true);
    handleLocationCheck(false);
});

function removeAllLoadingIndicators() {
    try {
        const indicators = document.querySelectorAll('.typing-indicator');
        indicators.forEach(ind => {
            const msg = ind.closest('.message');
            if (msg) msg.remove();
        });
    } catch (e) {
        console.error("Error cleaning indicators:", e);
    }
}

// --- Initialization & Simple Permission Logic ---
document.addEventListener('DOMContentLoaded', () => {
    initializeMap();
    loadHistory(); // Reload history first

    // Safety: Remove any indicators that might have leaked into history or remained stuck
    removeAllLoadingIndicators();

    // Try to restore cached location
    const cachedLocation = sessionStorage.getItem('last_location');
    if (cachedLocation) {
        currentUserLocation = JSON.parse(cachedLocation);
        updateMap(currentUserLocation.lat, currentUserLocation.lng, null);
    }

    // Send welcome message
    if (!sessionStorage.getItem('welcomeShown')) {
        setTimeout(() => {
            appendMessage('ai', 'Xin chào! Chúc bạn một ngày tốt lành! 😊 Bạn muốn tìm mua sản phẩm gì hôm nay ạ?');
            sessionStorage.setItem('welcomeShown', 'true');

            // Proactively ask for permission using simple browser confirm()
            if (!currentUserLocation) {
                setTimeout(() => {
                    const ask = window.confirm("Cửa hàng cần truy cập vị trí của bạn để tìm shop gần nhất. Bạn có đồng ý không?");
                    if (ask) {
                        handleLocationCheck(true);
                    }
                }, 1500);
            }
        }, 500);
    }

    // Process product interest from query params (when redirected from /view page)
    const urlParams = new URLSearchParams(window.location.search);
    const productId = urlParams.get('product_interest');
    const productName = urlParams.get('product_name');
    const zaloFromUrl = urlParams.get('zalo'); // PERSISTENCE FROM PROXY
    const staffZaloFromUrl = urlParams.get('staff_zalo'); // PERSISTENCE FROM PROXY

    console.log("DEBUG: Init Params - ID:", productId, "Name:", productName, "Zalo:", zaloFromUrl, "Staff Zalo:", staffZaloFromUrl);

    // FIX: Clean corrupted avatar from localStorage if present
    const userPic = localStorage.getItem('user_picture');
    if (userPic && (userPic === '[object Object]' || userPic.includes('object'))) {
        console.warn("Found corrupted user_picture, clearing.");
        localStorage.removeItem('user_picture');
    }
    // FIX: Clean corrupted zalo_code_verifier from localStorage if present
    const zaloCodeVerifier = localStorage.getItem('zalo_code_verifier');
    if (zaloCodeVerifier && (zaloCodeVerifier === '[object Object]' || zaloCodeVerifier.includes('object'))) {
        console.warn("Found corrupted zalo_code_verifier, clearing.");
        localStorage.removeItem('zalo_code_verifier');
    }

    if (productId && productName && !sessionStorage.getItem('productProcessed_' + productId)) {
        // Prevent re-processing on refresh
        sessionStorage.setItem('productProcessed_' + productId, 'true');

        const decodedName = decodeURIComponent(productName);

        // Store in global for Lead Form to use
        window.currentProductContext = decodedName;

        const userName = localStorage.getItem('user_name') || 'Khách';

        // Restore format: [Hệ thống ghi nhận user **Nguyễn Xuân Tài** đang quan tâm sản phẩm: **Tên SP**]
        const systemMessage = `[Hệ thống ghi nhận user ** ${userName} ** đang quan tâm sản phẩm: ** ${decodedName} **]`;
        appendMessage('ai', systemMessage);

        // ADD TO ACCUMULATION ARRAY (when user views product)
        window.interestedProducts.push({
            shopName: '', // Will be filled from API call below
            groupLink: zaloFromUrl || '',
            productName: decodedName,
            timestamp: new Date().toLocaleString(),
            sent: false // Tracking flag
        });
        saveInterestedProducts();
        console.log(`✅ Added to interest list: ${decodedName} (Total: ${window.interestedProducts.length})`);

        // Note: Global function handleDualZaloAction defined at top of file

        // OPTIMIZATION: Use URL params ONLY if we have BOTH Link Group AND Link Staff
        // This prevents the "NULL" Staff ID issue if the URL is old/incomplete
        if (zaloFromUrl && zaloFromUrl.includes('http') && staffZaloFromUrl && staffZaloFromUrl.length > 5) {
            const safeLink = zaloFromUrl.trim();
            const safeStaffZalo = staffZaloFromUrl.trim();
            const productContext = decodedName || "Sản phẩm";

            const msg = encodeURIComponent(`Chào bạn, tôi quan tâm sản phẩm: ${productContext}.Nhờ hỗ trợ!`);
            const staffLink = safeStaffZalo ? `https://zalo.me/${safeStaffZalo}?text=${msg}` : "";

            let buttonsHtml = `<div>Bấm vào link bên dưới để kết nối:</div>`;

            // Button 1: Chat with Staff (REMOVED per user request)


            // Button 2: Join Group (Secondary)
            if (safeLink) {
                buttonsHtml += `<a href="${safeLink}" target="_blank" style="display: block; text-align: center; margin-top: 5px; padding: 8px 16px; background: #e0e0e0; color: #333; text-decoration: none; border-radius: 4px; font-weight: bold;">📢 Vào Nhóm Săn Sale</a>`;
            }

            appendMessage('ai', buttonsHtml);
            return;
        }

        const statusMsg = renderMessage('ai', '<div class="typing-indicator">Đang lấy thông tin shop...</div>', false);
        setTimeout(async () => {
            try {
                // Use standard API path
                const response = await fetch(`${window.location.origin}/api/product-info/${productId}`);
                const data = await response.json();
                console.log("DEBUG: Product Info Data:", data);

                if (data && !data.error) {
                    const shopDisplay = data.shop_name || "Cửa hàng";

                    // UPDATE shop name in accumulated products (match by product name)
                    if (window.interestedProducts.length > 0) {
                        // Find the product that matches this API call's product name
                        const matchingProduct = window.interestedProducts.find(p =>
                            p.productName === decodedName && p.shopName === ''
                        );

                        if (matchingProduct) {
                            matchingProduct.shopName = shopDisplay;
                            saveInterestedProducts();
                            console.log(`📝 Updated shop name for "${decodedName}": ${shopDisplay}`);
                        }
                    }

                    // UPDATE CONTEXT TIMER
                    window.lastSearchTime = Date.now();

                    // FIX: Strict type coercion to prevent [object Object]
                    let finalZalo = "";
                    if (data.zalo_link) {
                        if (typeof data.zalo_link === 'string') {
                            finalZalo = data.zalo_link.trim();
                        } else {
                            // Defensive: try to stringify or fallback
                            try {
                                finalZalo = String(data.zalo_link);
                                if (finalZalo === '[object Object]') finalZalo = "";
                            } catch (e) { finalZalo = ""; }
                        }
                    }

                    if (finalZalo) {
                        // Use Dual Action Button instead of Markdown Link
                        const safeStaff = data.staff_zalo || '';
                        const pName = data.product_name || data.name || "Sản phẩm";

                        const msg = encodeURIComponent(`Chào bạn, tôi quan tâm sản phẩm: ${pName}. Nhờ hỗ trợ!`);
                        const staffLink = safeStaff ? `https://zalo.me/${safeStaff}?text=${msg}` : "";

                        let buttonsHtml = `<div>Kết nối với shop <b>${shopDisplay}</b>:</div>`;

                        // Button 1: Chat with Staff (REMOVED per user request)


                        // Button 2: Join Group (Secondary)
                        if (finalZalo) {
                            buttonsHtml += `<a href="${finalZalo}" target="_blank" style="display: block; text-align: center; margin-top: 5px; padding: 8px 16px; background: #e0e0e0; color: #333; text-decoration: none; border-radius: 4px; font-weight: bold;" onclick="trackInterest(event, '${safeEncode(shopDisplay)}', '${safeEncode(finalZalo)}', '${safeEncode(pName)}')">📢 Vào Nhóm Săn Sale</a>`;
                        }

                        appendMessage('ai', buttonsHtml);
                    } else {
                        appendMessage('ai', `Cửa hàng **${shopDisplay}** hiện chưa cập nhật link Zalo. Bạn có muốn nhắn tin hỏi shop không?`);
                    }
                } else {
                    console.error("API Error or Empty Data:", data);
                    appendMessage('ai', "Không tìm thấy thông tin shop cho sản phẩm này.");
                }
            } catch (err) {
                console.error("Error fetching product info:", err);
            } finally {
                if (statusMsg) statusMsg.remove();
            }
        }, 500);

        // CLEARING URL REDIRECT removed as per user request to keep full path/params
        // window.history.replaceState({}, document.title, window.location.pathname);

        // Suppress welcome message for this mission-specific landing
        sessionStorage.setItem('welcomeShown', 'true');
    }

    console.log("Chat initialized V3.8");
});

// Reset persistence only on logout if needed (optional, keeping current localStorage behavior)
window.addEventListener('beforeunload', () => {
    // We NO LONGER clear interestedProducts here to allow navigation persistence
    // Data is stored in localStorage to survive tab closure/crashes
    console.log("💾 Maximum Persistence active: interestedProducts preserved in localStorage.");
});

// --- Helper for Product Pagination ---
function revealNextBatch(btn) {
    const productList = btn.parentElement;
    const hiddenItems = productList.querySelectorAll('.product-item.hidden-product');

    // Convert to array to slice
    const itemsToReveal = Array.from(hiddenItems).slice(0, 3);

    itemsToReveal.forEach(item => {
        item.style.display = ''; // Reset display to default (block/flex)
        item.classList.remove('hidden-product');
    });

    // Check remaining hidden items
    const remaining = hiddenItems.length - itemsToReveal.length;

    if (remaining > 0) {
        btn.innerText = `Xem thêm (${remaining} sản phẩm)`;
    } else {
        btn.style.display = 'none'; // Hide button if no more items
    }
}

// --- LEAD GENERATION TRACKING WITH POPUP ---
let pendingLeadData = null; // Store data while waiting for phone input

// 1. Inject Modal HTML into DOM
function injectPhoneModal() {
    const modalHtml = `
    <!-- Bootstrap Modal for Phone Input -->
    <div class="modal fade" id="phoneInputModal" tabindex="-1" aria-labelledby="phoneModalLabel" aria-hidden="true" data-bs-backdrop="static" data-bs-keyboard="false">
        <div class="modal-dialog modal-dialog-centered">
            <div class="modal-content" style="border-radius: 16px; border: none; box-shadow: 0 10px 30px rgba(0,0,0,0.2);">
                <div class="modal-header" style="background: linear-gradient(135deg, #6a11cb 0%, #2575fc 100%); color: white; border-top-left-radius: 16px; border-top-right-radius: 16px;">
                    <h5 class="modal-title" id="phoneModalLabel">🎁 Tham gia nhóm săn sale</h5>
                    <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Close" onclick="confirmLead('exit')"></button>
                </div>
                <div class="modal-body text-center p-4">
                    <div class="mb-3">
                        <i class="fas fa-gift fa-3x text-warning mb-3"></i>
                        <p class="fs-5 fw-bold" style="color: #333;">Để lại SĐT để được Admins hỗ trợ rieng nhé!</p>
                        <p class="text-muted small">Chúng tôi sẽ add bạn vào nhóm Zalo VIP & Gửi mã giảm giá.</p>
                    </div>
                    <div class="form-floating mb-3">
                        <input type="tel" class="form-control" id="userPhoneInput" placeholder="Số điện thoại của bạn" style="border-radius: 10px;">
                        <label for="userPhoneInput">Nhập số điện thoại (Zalo)</label>
                    </div>
                </div>
                <div class="modal-footer justify-content-between border-0 pb-4">
                    <button type="button" class="btn btn-outline-secondary px-3" style="border-radius: 20px;" onclick="confirmLead('exit')">
                        ❌ Thoát
                    </button>
                    <button type="button" class="btn btn-outline-primary px-3" style="border-radius: 20px;" onclick="confirmLead('skip')">
                        ⏩ Không cần
                    </button>
                    <button type="button" class="btn btn-primary px-4 fw-bold" style="border-radius: 20px; background: linear-gradient(135deg, #6a11cb 0%, #2575fc 100%); border: none;" onclick="confirmLead('submit')">
                        Xác nhận & Vào nhóm 🚀
                    </button>
                </div>
            </div>
        </div>
    </div>
    `;
    document.body.insertAdjacentHTML('beforeend', modalHtml);
}

// Ensure Modal is injected on load
document.addEventListener('DOMContentLoaded', () => {
    injectPhoneModal();
});

// 2. Main Entry Point: Triggered by Button Click
function trackInterest(event, shopNameEncoded, groupLinkEncoded, productNameEncoded) {
    if (event) event.preventDefault(); // Stop immediate navigation

    // Decode Data
    const shopName = decodeURIComponent(shopNameEncoded);
    const groupLink = decodeURIComponent(groupLinkEncoded);
    let productName = decodeURIComponent(productNameEncoded);

    // FIX: If productName is generic "Sản phẩm", try to find real name from array
    if (productName === "Sản phẩm" || productName === shopName) {
        // Search from newest to oldest, prioritizing NOT SENT items
        const candidate = [...window.interestedProducts].reverse().find(p =>
            p.shopName === shopName && !p.sent
        ) || [...window.interestedProducts].reverse().find(p => p.shopName === shopName);

        if (candidate && candidate.productName !== "Sản phẩm") {
            productName = candidate.productName;
            console.log(`🔄 Resolved "${shopName}" -> "${productName}" (Recent Priority)`);
        }
    }

    // ADD TO ACCUMULATION (for direct "Join Group" clicks without viewing product detail)
    // Check if already exists
    const existingIndex = window.interestedProducts.findIndex(p =>
        p.productName === productName
    );

    if (existingIndex === -1) {
        // New product
        window.interestedProducts.push({
            shopName,
            groupLink,
            productName,
            timestamp: new Date().toLocaleString(),
            sent: false // Tracking flag
        });
        saveInterestedProducts();
        console.log(`✅ Added to interest list: ${productName} (Total: ${window.interestedProducts.length})`);
    } else {
        const product = window.interestedProducts[existingIndex];
        if (product.sent) {
            // User wants to interest again - Re-activate!
            product.sent = false;
            product.timestamp = new Date().toLocaleString();
            saveInterestedProducts();
            console.log(`🔄 Re-activated interest for: ${productName}`);
        } else {
            console.log(`⚠️ Product already in queue: ${productName}`);
        }
    }

    // Save to global for Modal callback
    pendingLeadData = {
        shopName,
        groupLink,
        productName
    };

    // CHECK FOR PERSISTED PHONE - To avoid repeating modal on mobile UX
    const storedPhone = localStorage.getItem('user_phone');
    if (storedPhone && storedPhone !== "None") {
        console.log("📱 Using stored phone:", storedPhone);
        submitLeadPayload(storedPhone);
        return;
    }

    // Show Modal
    const modalEl = document.getElementById('phoneInputModal');
    if (typeof bootstrap !== 'undefined' && modalEl) {
        const modal = new bootstrap.Modal(modalEl);
        modal.show();
    } else {
        // Fallback if Bootstrap not loaded: proceed without phone
        console.warn("Bootstrap Modal not found, skipping phone input.");
        submitLeadPayload(null);
    }
}

// 3. User Decision Handler (Submit or Skip or Exit)
function confirmLead(action) {
    const modalEl = document.getElementById('phoneInputModal');
    const modal = bootstrap.Modal.getInstance(modalEl);

    // ACTION 1: Exit - Close modal and do nothing
    if (action === 'exit') {
        if (modal) modal.hide();
        console.log("❌ User exited modal");
        return;
    }

    // ACTION 2 & 3: Skip or Submit
    let phone = "None"; // Default

    if (action === 'submit') {
        const input = document.getElementById('userPhoneInput');
        if (input && input.value.trim().length > 0) {
            phone = input.value.trim();
            localStorage.setItem('user_phone', phone); // PERSIST
        } else {
            // User clicked Submit but empty? Alert
            alert("Vui lòng nhập số điện thoại hoặc chọn 'Không cần'");
            return; // Stay in modal
        }
    }

    // Hide Modal
    if (modal) modal.hide();

    // Proceed to send data
    submitLeadPayload(phone);
}

// 4. Submit Data & Navigate
async function submitLeadPayload(phone) {
    if (!pendingLeadData) return;

    const { groupLink } = pendingLeadData;

    // A. Open Group Link (UX Priority - Immediate)
    window.open(groupLink, '_blank');

    // B. Send ALL accumulated products as separate rows
    if (window.interestedProducts.length === 0) {
        console.warn("⚠️ No products in interest list!");
        return;
    }

    try {
        // Collect Context (shared for all products)
        const contextMsgs = chatHistory.filter(item => {
            return item.sender === 'user' || item.type === 'trigger';
        }).slice(-10); // Increase to 10 for better context
        const contextStr = contextMsgs.map(m => m.text).join(" - ");

        // Only send products that haven't been submitted yet
        const unsentProducts = window.interestedProducts.filter(p => !p.sent);

        if (unsentProducts.length === 0) {
            console.log(`ℹ️ All ${window.interestedProducts.length} products already sent previously.`);
        } else {
            console.log(`� Submitting ${unsentProducts.length} new products to sheet...`);

            // Send each product as a separate row
            for (const product of unsentProducts) {
                const payload = {
                    user_name: localStorage.getItem('user_name') || "Khách",
                    user_id: localStorage.getItem('session_id') || "guest",
                    product_name: product.productName,
                    shop_name: product.shopName,
                    chat_context: contextStr || "User clicked Interest",
                    phone: phone, // Actual Phone or "None"
                    zalo_contact: phone, // Backward compatibility
                    avatar_url: localStorage.getItem('user_picture') || "",
                    zalo_group_link: product.groupLink,
                    timestamp: product.timestamp
                };

                // Send API (fire and forget)
                fetch('/api/submit-lead', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                }).then(() => {
                    console.log(`✅ Sent: ${product.productName}`);
                    product.sent = true; // Mark as sent in memory
                    saveInterestedProducts(); // Persist the 'sent' state
                }).catch(e => {
                    console.error(`❌ Failed: ${product.productName}`, e);
                });
            }
        }

        console.log(`✅ Submission process complete. Array preserved (Total: ${window.interestedProducts.length}).`);

    } catch (e) {
        console.error("Tracking Error:", e);
    }

    // Reset
    pendingLeadData = null;
    document.getElementById('userPhoneInput').value = ''; // Clear input
}

function safeEncode(str) {
    if (!str) return '';
    return encodeURIComponent(str).replace(/'/g, "%27");
}
