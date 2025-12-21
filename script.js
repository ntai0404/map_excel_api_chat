
let map;
let userMarker;
let storeMarkers = L.featureGroup();
let currentUserLocation = null;
let chatHistory = []; // Global history array

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
                    products: store.products || []
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

    stores.forEach(store => {
        const card = document.createElement('div');
        card.className = 'store-card';
        card.onclick = () => focusOnStore(store.lat, store.lng, store.name);
        card.style.cursor = 'pointer';

        card.innerHTML = `
            <div class="store-name">${store.name}</div>
            <div class="store-address">${store.description}</div>
            <div class="store-distance">📏 Cách bạn: ${store.distance_km ? store.distance_km.toFixed(1) : '?'} km</div>
            
            ${store.products && store.products.length > 0 ? `
                <div class="product-list">
                    ${store.products.map(p => {
            // Inject Zalo link into the proxy URL for persistence
            let finalLink = p.link || '#';
            if (store.zalo_group_link && finalLink !== '#') {
                const separator = finalLink.includes('?') ? '&' : '?';
                finalLink += `${separator}zalo=${encodeURIComponent(store.zalo_group_link)}`;
            }
            return `
                        <div class="product-item">
                            <img src="${p.image_url || 'https://via.placeholder.com/120'}" class="product-img" onerror="this.src='https://via.placeholder.com/120?text=No+Image'">
                            <div class="product-info">
                                <div class="product-name" title="${p.name}">${p.name}</div>
                                <div class="product-price">${p.price}</div>
                                <a href="${finalLink}" target="_self" class="product-link-btn" onclick="event.stopPropagation()">🔗 Xem sản phẩm</a>
                            </div>
                        </div>
                        `;
        }).join('')}
                </div>
            ` : ''}

            ${store.zalo_group_link ?
                `<a href="${store.zalo_group_link}" target="_blank" class="zalo-btn" onclick="event.stopPropagation()">💬 Tham gia nhóm Zalo</a>`
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
                renderMessage('ai', `Đã xác định được vị trí của bạn: Lat ${location.lat}, Lng ${location.lng}. Tôi có thể giúp bạn tìm gì gần đây?`, true);
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

    console.log("DEBUG: Init Params - ID:", productId, "Name:", productName, "Zalo:", zaloFromUrl);

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
        const userName = localStorage.getItem('user_name') || 'Khách';

        // Restore format: [Hệ thống ghi nhận user **Nguyễn Xuân Tài** đang quan tâm sản phẩm: **Tên SP**]
        const systemMessage = `[Hệ thống ghi nhận user **${userName}** đang quan tâm sản phẩm: **${decodedName}**]`;
        appendMessage('ai', systemMessage);

        // OPTIMIZATION: If Zalo link preserved from Proxy, show immediately!
        // Use strict check and raw HTML to bypass Markdown issues
        if (zaloFromUrl && zaloFromUrl !== "undefined" && zaloFromUrl !== "null" && zaloFromUrl.startsWith('http')) {
            const safeLink = zaloFromUrl.trim();
            // Use Raw HTML to ensure link works
            appendMessage('ai', `Bấm vào link Zalo bên dưới để chat với shop ngay! 👇<br><br><a href="${safeLink}" target="_blank" style="color: #0068FF; font-weight: bold; text-decoration: underline;">Kết nối Zalo</a>`);
            return; // Skip API call
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
                        appendMessage('ai', `Bấm vào link Zalo bên dưới để chat với shop **${shopDisplay}** ngay! 👇\n\n[Kết nối Zalo](${finalZalo})`);
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
