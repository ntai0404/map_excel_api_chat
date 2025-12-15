
let map;
let userMarker;
let storeMarkers = L.featureGroup();
let currentUserLocation = null;

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
}

function updateMap(userLat, userLng, stores) {
    if (userMarker) {
        map.removeLayer(userMarker);
    }

    if (userLat && userLng) {
        userMarker = L.marker([userLat, userLng]).addTo(map)
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

                L.marker([store.lat, store.lng])
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
            map.setView([stores[0].lat, stores[0].lng], 13);
        }
    }
}

// 3.2. Xử lý Vị trí (Geolocation)
function getUserLocation() {
    return new Promise((resolve, reject) => {
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(
                (position) => {
                    currentUserLocation = {
                        lat: position.coords.latitude,
                        lng: position.coords.longitude
                    };
                    // Pass null for stores to preserve existing markers
                    updateMap(currentUserLocation.lat, currentUserLocation.lng, null);
                    resolve(currentUserLocation);
                },
                (error) => {
                    console.error("Error getting user location:", error);
                    // Fallback: If we already have a location, use it!
                    if (currentUserLocation) {
                        console.log("Using cached location after error.");
                        resolve(currentUserLocation);
                    } else {
                        alert("Unable to retrieve your location. Please allow location access or type your address.");
                        resolve(null);
                    }
                }
            );
        } else {
            alert("Geolocation is not supported by this browser.");
            // If geolocation is not supported, we should not clear a potentially existing cached location.
            // Only resolve null if there's no cached location.
            if (currentUserLocation) {
                console.log("Geolocation not supported, but using cached location.");
                resolve(currentUserLocation);
            } else {
                currentUserLocation = null;
                resolve(null);
            }
        }
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
    const messageElement = document.createElement('div');
    messageElement.classList.add('message', sender);

    // Parse Markdown for AI messages, keep plain text for user
    const content = sender === 'ai' ? marked.parse(text) : text;

    messageElement.innerHTML = `<div class="message-bubble">${content}</div>`;
    chatMessages.appendChild(messageElement);
    chatMessages.scrollTop = chatMessages.scrollHeight; // Auto-scroll to bottom
}

async function sendMessage() {
    const userMessage = chatInput.value.trim();
    if (userMessage === '') return;

    appendMessage('user', userMessage);
    chatInput.value = '';

    appendMessage('ai', '<div class="typing-indicator">AI is typing...</div>'); // Typing indicator

    // Use cached location if available to prevent repeated prompts
    const location = currentUserLocation || await getUserLocation();

    const aiResponse = await fetchAIResponse(userMessage, location);

    // Remove typing indicator
    const typingIndicator = chatMessages.querySelector('.typing-indicator');
    if (typingIndicator) {
        typingIndicator.parentNode.remove();
    }

    if (!aiResponse.trigger_location) {
        appendMessage('ai', aiResponse.text);
    }

    // Render Store Cards
    if (aiResponse.map_data && aiResponse.map_data.store_markers && aiResponse.map_data.store_markers.length > 0) {
        const storeListHtml = document.createElement('div');
        storeListHtml.className = 'store-list';

        // DEBUG: Log product data to check if 'link' field exists
        console.log('🔍 DEBUG: Store data from backend:', aiResponse.map_data.store_markers);

        aiResponse.map_data.store_markers.forEach(store => {
            // DEBUG: Log each product's link status
            if (store.products) {
                store.products.forEach(p => {
                    console.log(`Product: ${p.name}, Has Link: ${!!p.link}, Link: ${p.link}`);
                });
            }
            const card = document.createElement('div');
            card.className = 'store-card';
            // Add click event to focus map
            card.onclick = () => focusOnStore(store.lat, store.lng, store.name);
            card.style.cursor = 'pointer'; // Show pointer to indicate clickable

            card.innerHTML = `
                <div class="store-name">${store.name}</div>
                <div class="store-address">${store.description}</div>
                <div class="store-distance">📏 Cách bạn: ${store.distance_km ? store.distance_km.toFixed(1) : '?'} km</div>
                
                ${store.products && store.products.length > 0 ? `
                    <div class="product-list">
                        ${store.products.map(p => `
                            <div class="product-item">
                                <img src="${p.image_url || 'https://via.placeholder.com/120'}" class="product-img" onerror="this.src='https://via.placeholder.com/120?text=No+Image'">
                                <div class="product-info">
                                    <div class="product-name" title="${p.name}">${p.name}</div>
                                    <div class="product-price">${p.price}</div>
                                    ${p.link ? `<a href="${p.link}" target="_blank" class="product-link-btn" onclick="event.stopPropagation()">🔗 Xem sản phẩm</a>` : ''}
                                </div>
                            </div>
                        `).join('')}
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

        updateMap(
            aiResponse.map_data.user_marker ? aiResponse.map_data.user_marker.lat : null,
            aiResponse.map_data.user_marker ? aiResponse.map_data.user_marker.lng : null,
            aiResponse.map_data.store_markers
        );
    }

    // Auto-trigger location if backend requested it
    if (aiResponse.trigger_location) {
        console.log("Backend requested location trigger.");
        handleLocationCheck(true);
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

// 3.5. Xử lý logic lấy vị trí (Refactored)
async function handleLocationCheck(isAutoTriggered = false) {
    if (!isAutoTriggered) {
        appendMessage('user', 'Vị trí của tôi');
    }

    appendMessage('ai', '<div class="typing-indicator">Đang lấy vị trí...</div>');
    const location = await getUserLocation();

    const typingIndicator = chatMessages.querySelector('.typing-indicator');
    if (typingIndicator) {
        typingIndicator.parentNode.remove();
    }

    if (location) {
        appendMessage('ai', `Đã xác định được vị trí của bạn: Lat ${location.lat}, Lng ${location.lng}. Tôi có thể giúp bạn tìm gì gần đây?`);
    } else {
        appendMessage('ai', 'Không thể lấy vị trí của bạn. Vui lòng thử lại hoặc nhập địa chỉ cụ thể.');
    }
}

locationButton.addEventListener('click', () => handleLocationCheck(false));

// Initialize map on load
document.addEventListener('DOMContentLoaded', () => {
    initializeMap();
    getUserLocation(); // Get initial user location

    // Send welcome message only once per session
    if (!sessionStorage.getItem('welcomeShown')) {
        setTimeout(() => {
            appendMessage('ai', 'Xin chào! Chúc bạn một ngày tốt lành! 😊 Bạn muốn tìm mua sản phẩm gì hôm nay ạ?');
            sessionStorage.setItem('welcomeShown', 'true');
        }, 500);
    }
});

