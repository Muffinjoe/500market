// ---- Finnhub Real-Time Price Updates ----
// Connects via WebSocket, subscribes to visible stocks, updates table in real-time

const FINNHUB_KEY = 'd6ismgpr01qleu95dlfgd6ismgpr01qleu95dlg0';
let ws = null;
let subscribedSymbols = new Set();
let livePrices = {};  // ticker → { price, timestamp }
let wsConnected = false;
let reconnectTimer = null;

// Flash animation for price updates
const flashStyle = document.createElement('style');
flashStyle.textContent = `
    @keyframes price-flash-up { 0% { background: rgba(22,199,132,0.2); } 100% { background: transparent; } }
    @keyframes price-flash-down { 0% { background: rgba(234,57,67,0.2); } 100% { background: transparent; } }
    .price-flash-up { animation: price-flash-up 0.8s ease-out; }
    .price-flash-down { animation: price-flash-down 0.8s ease-out; }
    .live-badge { display: inline-flex; align-items: center; gap: 4px; font-size: 11px; font-weight: 600; color: #16c784; }
    .live-dot { width: 6px; height: 6px; border-radius: 50%; background: #16c784; animation: pulse-dot 1.5s infinite; }
    @keyframes pulse-dot { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }
`;
document.head.appendChild(flashStyle);

function connectWebSocket() {
    if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) return;

    ws = new WebSocket(`wss://ws.finnhub.io?token=${FINNHUB_KEY}`);

    ws.onopen = () => {
        wsConnected = true;
        updateLiveBadge(true);
        // Re-subscribe to any symbols we were tracking
        subscribedSymbols.forEach(sym => {
            ws.send(JSON.stringify({ type: 'subscribe', symbol: sym }));
        });
    };

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'trade' && data.data) {
            data.data.forEach(trade => {
                const symbol = trade.s;
                const price = trade.p;
                const oldPrice = livePrices[symbol]?.price;

                livePrices[symbol] = {
                    price: price,
                    timestamp: trade.t,
                    direction: oldPrice ? (price > oldPrice ? 'up' : price < oldPrice ? 'down' : 'flat') : 'flat',
                };
            });
            // Batch DOM updates
            requestAnimationFrame(updateVisiblePrices);
        }
    };

    ws.onclose = () => {
        wsConnected = false;
        updateLiveBadge(false);
        // Reconnect after 5 seconds
        if (!reconnectTimer) {
            reconnectTimer = setTimeout(() => {
                reconnectTimer = null;
                connectWebSocket();
            }, 5000);
        }
    };

    ws.onerror = () => {
        ws.close();
    };
}

function subscribeToSymbols(symbols) {
    const newSymbols = symbols.filter(s => !subscribedSymbols.has(s));
    const oldSymbols = [...subscribedSymbols].filter(s => !symbols.includes(s));

    // Unsubscribe from stocks no longer visible
    oldSymbols.forEach(sym => {
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'unsubscribe', symbol: sym }));
        }
        subscribedSymbols.delete(sym);
    });

    // Subscribe to new visible stocks
    newSymbols.forEach(sym => {
        subscribedSymbols.add(sym);
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'subscribe', symbol: sym }));
        }
    });
}

function updateVisiblePrices() {
    const rows = document.querySelectorAll('#stockBody tr');
    rows.forEach(row => {
        const nameCell = row.querySelector('.stock-ticker');
        if (!nameCell) return;
        const ticker = nameCell.textContent.split(' · ')[0].trim();

        const liveData = livePrices[ticker];
        if (!liveData) return;

        const priceCell = row.querySelector('.td-price');
        if (!priceCell) return;

        const currentText = priceCell.textContent;
        const newText = formatPriceLive(liveData.price);

        if (currentText !== newText) {
            priceCell.textContent = newText;

            // Flash animation
            priceCell.classList.remove('price-flash-up', 'price-flash-down');
            void priceCell.offsetWidth; // Force reflow
            if (liveData.direction === 'up') {
                priceCell.classList.add('price-flash-up');
            } else if (liveData.direction === 'down') {
                priceCell.classList.add('price-flash-down');
            }
        }
    });

    // Update S&P 500 proxy (SPY × 10 ≈ S&P 500)
    if (livePrices['SPY']) {
        const spyPrice = livePrices['SPY'].price;
        const sp500Approx = spyPrice * 10;
        const heroPrice = document.getElementById('heroPrice');
        if (heroPrice) {
            heroPrice.textContent = sp500Approx.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
        }
        const spIndex = document.getElementById('spIndex');
        if (spIndex) {
            spIndex.textContent = sp500Approx.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
        }
    }

    // Update detail panel if open
    const detailPrice = document.querySelector('.detail-price');
    if (detailPrice) {
        const detailTicker = document.querySelector('.detail-ticker');
        if (detailTicker) {
            const ticker = detailTicker.textContent.trim();
            const ld = livePrices[ticker];
            if (ld) {
                const newPrice = formatPriceLive(ld.price);
                if (detailPrice.textContent !== newPrice) {
                    detailPrice.textContent = newPrice;
                    detailPrice.classList.remove('price-flash-up', 'price-flash-down');
                    void detailPrice.offsetWidth;
                    detailPrice.classList.add(ld.direction === 'up' ? 'price-flash-up' : 'price-flash-down');
                }
            }
        }
    }
}

function formatPriceLive(n) {
    if (n >= 1000) return '$' + n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    return '$' + n.toFixed(2);
}

function updateLiveBadge(connected) {
    let badge = document.getElementById('liveBadge');
    if (!badge) {
        badge = document.createElement('span');
        badge.id = 'liveBadge';
        badge.className = 'live-badge';
        const topBar = document.getElementById('lastUpdated');
        if (topBar) topBar.parentNode.insertBefore(badge, topBar);
    }
    if (connected) {
        badge.innerHTML = '<span class="live-dot"></span> LIVE';
        badge.style.display = '';
    } else {
        badge.style.display = 'none';
    }
}

// Hook into render to subscribe to visible stocks
const _originalRender = typeof render === 'function' ? render : null;

function startLiveUpdates() {
    connectWebSocket();

    // Also subscribe to SPY for S&P 500 proxy
    subscribedSymbols.add('SPY');

    // Override render to update subscriptions when table changes
    if (_originalRender) {
        const origRender = _originalRender;
        window.renderWithLive = function() {
            origRender();
            // After rendering, subscribe to visible stocks
            setTimeout(() => {
                const visibleTickers = [];
                document.querySelectorAll('#stockBody .stock-ticker').forEach(el => {
                    const ticker = el.textContent.split(' · ')[0].trim();
                    if (ticker) visibleTickers.push(ticker);
                });
                visibleTickers.push('SPY');
                subscribeToSymbols(visibleTickers);
            }, 100);
        };
    }
}

// Start when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', startLiveUpdates);
} else {
    startLiveUpdates();
}

// Also subscribe after each render
const renderObserver = new MutationObserver(() => {
    const visibleTickers = [];
    document.querySelectorAll('#stockBody .stock-ticker').forEach(el => {
        const ticker = el.textContent.split(' · ')[0].trim();
        if (ticker) visibleTickers.push(ticker);
    });
    if (visibleTickers.length > 0) {
        visibleTickers.push('SPY');
        subscribeToSymbols(visibleTickers);
    }
});

const stockBody = document.getElementById('stockBody');
if (stockBody) {
    renderObserver.observe(stockBody, { childList: true });
}

// Disconnect when page is hidden to save resources
document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
        if (ws) ws.close();
    } else {
        connectWebSocket();
    }
});
