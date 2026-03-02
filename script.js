// State
let currentPage = 1;
const perPage = 50;
let currentSort = { key: 'marketCap', dir: 'desc' };
let currentSector = 'all';
let searchTerm = '';
let currentView = 'stocks'; // stocks | sectors | gainers | losers | watchlist

// Watchlist (localStorage + cookie for persistence)
function getCookie(name) {
    const match = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'));
    return match ? decodeURIComponent(match[2]) : null;
}
function setCookie(name, value, days) {
    const d = new Date();
    d.setTime(d.getTime() + days * 86400000);
    document.cookie = name + '=' + encodeURIComponent(value) + ';expires=' + d.toUTCString() + ';path=/;SameSite=Lax';
}

function loadWatchlist() {
    // Try localStorage first, then cookie fallback
    const ls = localStorage.getItem('500m_watchlist');
    if (ls) return JSON.parse(ls);
    const ck = getCookie('500m_watchlist');
    if (ck) return JSON.parse(ck);
    return [];
}
function saveWatchlist() {
    const val = JSON.stringify(watchlist);
    localStorage.setItem('500m_watchlist', val);
    setCookie('500m_watchlist', val, 365);
}

let watchlist = loadWatchlist();

function isWatched(ticker) { return watchlist.includes(ticker); }
function toggleWatch(ticker) {
    if (isWatched(ticker)) {
        watchlist = watchlist.filter(t => t !== ticker);
    } else {
        watchlist.push(ticker);
    }
    saveWatchlist();
}

// ---- Dark Mode ----
function initTheme() {
    const saved = localStorage.getItem('500m_theme');
    if (saved) {
        document.documentElement.setAttribute('data-theme', saved);
    } else if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
        document.documentElement.setAttribute('data-theme', 'dark');
    }
    updateThemeIcon();
}
function toggleTheme() {
    const current = document.documentElement.getAttribute('data-theme');
    const next = current === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('500m_theme', next);
    updateThemeIcon();
}
function updateThemeIcon() {
    const btn = document.getElementById('themeToggle');
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    btn.innerHTML = isDark ? '&#9728;' : '&#9790;';
    btn.title = isDark ? 'Switch to light mode' : 'Switch to dark mode';
}
document.getElementById('themeToggle').addEventListener('click', toggleTheme);
initTheme();

// Format helpers
function formatCurrency(n) {
    if (n >= 1e12) return '$' + (n / 1e12).toFixed(2) + 'T';
    if (n >= 1e9) return '$' + (n / 1e9).toFixed(2) + 'B';
    if (n >= 1e6) return '$' + (n / 1e6).toFixed(2) + 'M';
    return '$' + n.toLocaleString();
}

function formatPrice(n) {
    if (n >= 1000) return '$' + n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    return '$' + n.toFixed(2);
}

function formatVolume(n) {
    if (n >= 1e9) return '$' + (n / 1e9).toFixed(1) + 'B';
    if (n >= 1e6) return '$' + (n / 1e6).toFixed(1) + 'M';
    return '$' + n.toLocaleString();
}

function formatChange(val) {
    const cls = val >= 0 ? 'change-up' : 'change-down';
    const sign = val >= 0 ? '+' : '';
    return `<span class="${cls}">${sign}${val.toFixed(2)}%</span>`;
}

// Generate a deterministic sparkline from stock data
function generateSparkline(stock) {
    const w = 120, h = 32;
    const points = 28;
    const data = [];

    // Seed from ticker for deterministic results
    let seed = 0;
    for (let i = 0; i < stock.ticker.length; i++) seed += stock.ticker.charCodeAt(i) * (i + 1);

    function pseudoRandom() {
        seed = (seed * 16807 + 0) % 2147483647;
        return (seed & 0x7fffffff) / 0x7fffffff;
    }

    // Generate price-like walk
    let val = 50;
    const trend = stock.change7d > 0 ? 0.3 : -0.3;
    for (let i = 0; i < points; i++) {
        val += (pseudoRandom() - 0.48 + trend * 0.05) * 6;
        val = Math.max(10, Math.min(90, val));
        data.push(val);
    }

    // Normalize
    const min = Math.min(...data);
    const max = Math.max(...data);
    const range = max - min || 1;
    const normalized = data.map(v => ((v - min) / range) * (h - 4) + 2);

    // Build SVG path
    const stepX = w / (points - 1);
    let pathD = '';
    normalized.forEach((y, i) => {
        const x = i * stepX;
        const yFlip = h - y;
        pathD += i === 0 ? `M${x},${yFlip}` : ` L${x},${yFlip}`;
    });

    const color = stock.change7d >= 0 ? '#16c784' : '#ea3943';

    // Gradient fill
    const lastY = h - normalized[normalized.length - 1];
    const fillD = pathD + ` L${w},${h} L0,${h} Z`;
    const gradId = `grad-${stock.ticker}`;

    return `<svg width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" xmlns="http://www.w3.org/2000/svg">
        <defs>
            <linearGradient id="${gradId}" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stop-color="${color}" stop-opacity="0.15"/>
                <stop offset="100%" stop-color="${color}" stop-opacity="0"/>
            </linearGradient>
        </defs>
        <path d="${fillD}" fill="url(#${gradId})"/>
        <path d="${pathD}" fill="none" stroke="${color}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>`;
}

// Filter and sort data
function getFilteredData() {
    let data = [...SP500_STOCKS];

    // View-based filtering
    if (currentView === 'gainers') {
        data = data.filter(s => s.change1d > 0);
    } else if (currentView === 'losers') {
        data = data.filter(s => s.change1d < 0);
    } else if (currentView === 'watchlist') {
        data = data.filter(s => isWatched(s.ticker));
    }

    // Sector filter
    if (currentSector !== 'all') {
        data = data.filter(s => s.sector === currentSector);
    }

    // Search filter
    if (searchTerm) {
        const q = searchTerm.toLowerCase();
        data = data.filter(s =>
            s.name.toLowerCase().includes(q) ||
            s.ticker.toLowerCase().includes(q) ||
            s.sector.toLowerCase().includes(q)
        );
    }

    // Sort — gainers/losers default to sorting by 1d change
    let sortKey = currentSort.key;
    let sortDir = currentSort.dir;
    if (currentView === 'gainers' && currentSort.key === 'marketCap') {
        sortKey = 'change1d';
        sortDir = 'desc';
    } else if (currentView === 'losers' && currentSort.key === 'marketCap') {
        sortKey = 'change1d';
        sortDir = 'asc';
    }

    data.sort((a, b) => {
        let av = a[sortKey];
        let bv = b[sortKey];
        if (av == null) av = -Infinity;
        if (bv == null) bv = -Infinity;
        return sortDir === 'asc' ? av - bv : bv - av;
    });

    return data;
}

// Render table
function render() {
    const data = getFilteredData();
    const totalPages = Math.max(1, Math.ceil(data.length / perPage));
    if (currentPage > totalPages) currentPage = totalPages;

    const start = (currentPage - 1) * perPage;
    const pageData = data.slice(start, start + perPage);

    const tbody = document.getElementById('stockBody');
    tbody.innerHTML = '';

    pageData.forEach((stock, i) => {
        const row = document.createElement('tr');
        const logoUrl = `https://www.google.com/s2/favicons?domain=${stock.domain}&sz=128`;
        const starred = isWatched(stock.ticker);
        row.innerHTML = `
            <td class="td-star"><button class="star-btn ${starred ? 'starred' : ''}" data-ticker="${stock.ticker}" title="${starred ? 'Remove from watchlist' : 'Add to watchlist'}">&#9733;</button></td>
            <td class="td-rank">${stock.rank}</td>
            <td>
                <div class="td-name">
                    <img class="stock-logo" src="${logoUrl}" alt="${stock.ticker}" onerror="this.style.display='none';this.nextElementSibling.style.display='flex';">
                    <div class="stock-icon" style="background:${stock.color};display:none">${stock.ticker.substring(0, 2)}</div>
                    <div class="stock-info">
                        <span class="stock-name">${stock.name}</span>
                        <span class="stock-ticker">${stock.ticker} · ${stock.sector}</span>
                    </div>
                </div>
            </td>
            <td class="td-price">${formatPrice(stock.price)}</td>
            <td>${formatChange(stock.change1d)}</td>
            <td>${formatChange(stock.change7d)}</td>
            <td>${formatChange(stock.changeYtd)}</td>
            <td>${formatCurrency(stock.marketCap)}</td>
            <td>${formatVolume(stock.volume)}</td>
            <td>${stock.pe ? stock.pe.toFixed(1) : '—'}</td>
            <td class="td-sparkline">${generateSparkline(stock)}</td>
        `;
        row.addEventListener('click', (e) => {
            // Star button click
            if (e.target.closest('.star-btn')) {
                e.stopPropagation();
                toggleWatch(stock.ticker);
                render();
                return;
            }
            // Ctrl/Cmd+click or middle click → open stock page in new tab
            if (e.ctrlKey || e.metaKey || e.button === 1) {
                window.open('s/' + stock.ticker.toLowerCase().replace('.', '-') + '.html', '_blank');
                return;
            }
            openDetail(stock);
        });
        tbody.appendChild(row);
    });

    // Pagination
    document.getElementById('pageInfo').textContent = `Page ${currentPage} of ${totalPages}`;
    document.getElementById('prevPage').disabled = currentPage <= 1;
    document.getElementById('nextPage').disabled = currentPage >= totalPages;

    // Update sort headers
    document.querySelectorAll('th.sortable').forEach(th => {
        th.classList.remove('sort-asc', 'sort-desc');
        if (th.dataset.sort === currentSort.key) {
            th.classList.add(currentSort.dir === 'asc' ? 'sort-asc' : 'sort-desc');
        }
    });
}

// Event: Column sorting
document.querySelectorAll('th.sortable').forEach(th => {
    th.addEventListener('click', () => {
        const key = th.dataset.sort;
        if (currentSort.key === key) {
            currentSort.dir = currentSort.dir === 'asc' ? 'desc' : 'asc';
        } else {
            currentSort = { key, dir: 'desc' };
        }
        currentPage = 1;
        render();
    });
});

// Render sectors view
function renderSectors() {
    const container = document.getElementById('sectorsView');
    const sectors = {};

    SP500_STOCKS.forEach(s => {
        if (!sectors[s.sector]) sectors[s.sector] = [];
        sectors[s.sector].push(s);
    });

    const totalMarketCap = SP500_STOCKS.reduce((sum, s) => sum + s.marketCap, 0);

    container.innerHTML = '';
    Object.keys(sectors).sort().forEach(name => {
        const stocks = sectors[name];
        const sectorCap = stocks.reduce((sum, s) => sum + s.marketCap, 0);
        const avgChange = stocks.reduce((sum, s) => sum + s.change1d, 0) / stocks.length;
        const gainers = stocks.filter(s => s.change1d > 0).length;
        const pctOfTotal = ((sectorCap / totalMarketCap) * 100).toFixed(1);
        const barColor = avgChange >= 0 ? 'var(--green)' : 'var(--red)';

        // Top 3 by market cap
        const top3 = [...stocks].sort((a, b) => b.marketCap - a.marketCap).slice(0, 3);

        const card = document.createElement('div');
        card.className = 'sector-card';
        card.innerHTML = `
            <div class="sector-header">
                <span class="sector-name">${name}</span>
                <span class="sector-count">${stocks.length} stocks</span>
            </div>
            <div class="sector-stats">
                <div class="sector-stat">
                    <span class="sector-stat-label">Mkt Cap</span>
                    <span class="sector-stat-value">${formatCurrency(sectorCap)}</span>
                </div>
                <div class="sector-stat">
                    <span class="sector-stat-label">Avg 1d</span>
                    <span class="sector-stat-value ${avgChange >= 0 ? 'change-up' : 'change-down'}">${avgChange >= 0 ? '+' : ''}${avgChange.toFixed(2)}%</span>
                </div>
                <div class="sector-stat">
                    <span class="sector-stat-label">Advancing</span>
                    <span class="sector-stat-value" style="color:var(--green)">${gainers}/${stocks.length}</span>
                </div>
            </div>
            <div class="sector-bar">
                <div class="sector-bar-fill" style="width:${pctOfTotal}%;background:${barColor}"></div>
            </div>
            <div style="font-size:11px;color:var(--text-secondary);margin-top:4px">${pctOfTotal}% of S&P 500</div>
            <div class="sector-top-stocks">
                ${top3.map(s => `
                    <div class="sector-stock-row">
                        <span class="sector-stock-name">${s.ticker} — ${formatPrice(s.price)}</span>
                        <span class="sector-stock-change ${s.change1d >= 0 ? 'change-up' : 'change-down'}">${s.change1d >= 0 ? '+' : ''}${s.change1d.toFixed(2)}%</span>
                    </div>
                `).join('')}
            </div>
        `;
        card.addEventListener('click', () => {
            // Switch to stocks view filtered by this sector
            currentView = 'stocks';
            currentSector = name;
            currentSort = { key: 'marketCap', dir: 'desc' };
            currentPage = 1;
            document.querySelectorAll('.pill').forEach(p => {
                p.classList.toggle('active', p.dataset.sector === name);
            });
            switchView('stocks');
        });
        container.appendChild(card);
    });
}

// Switch between views
function switchView(view) {
    currentView = view;
    const tableView = document.getElementById('tableView');
    const sectorsView = document.getElementById('sectorsView');
    const pagination = document.querySelector('.pagination');
    const pills = document.querySelector('.sector-pills');

    // Update nav
    document.querySelectorAll('.nav a').forEach(a => {
        a.classList.toggle('nav-active', a.dataset.view === view);
    });

    if (view === 'sectors') {
        tableView.style.display = 'none';
        sectorsView.style.display = 'grid';
        pagination.style.display = 'none';
        pills.style.display = 'none';
        renderSectors();
    } else {
        tableView.style.display = '';
        sectorsView.style.display = 'none';
        pagination.style.display = '';
        pills.style.display = view === 'watchlist' ? 'none' : '';

        if (view === 'gainers') {
            currentSort = { key: 'change1d', dir: 'desc' };
        } else if (view === 'losers') {
            currentSort = { key: 'change1d', dir: 'asc' };
        }

        currentPage = 1;
        render();
    }
}

// Event: Nav links
document.querySelectorAll('.nav a').forEach(link => {
    link.addEventListener('click', (e) => {
        e.preventDefault();
        const view = link.dataset.view;
        if (view === 'stocks') {
            currentSector = 'all';
            currentSort = { key: 'marketCap', dir: 'desc' };
            document.querySelectorAll('.pill').forEach(p => {
                p.classList.toggle('active', p.dataset.sector === 'all');
            });
        }
        switchView(view);
    });
});

// Build sector pills dynamically from data
function buildSectorPills() {
    const container = document.getElementById('sectorPills');
    if (!container) return;

    const sectors = [...new Set(SP500_STOCKS.map(s => s.sector))].sort();

    container.innerHTML = '<button class="pill active" data-sector="all">All Sectors</button>';
    sectors.forEach(sector => {
        const count = SP500_STOCKS.filter(s => s.sector === sector).length;
        const btn = document.createElement('button');
        btn.className = 'pill';
        btn.dataset.sector = sector;
        btn.textContent = sector;
        container.appendChild(btn);
    });

    // Event listeners
    container.querySelectorAll('.pill').forEach(pill => {
        pill.addEventListener('click', () => {
            container.querySelectorAll('.pill').forEach(p => p.classList.remove('active'));
            pill.classList.add('active');
            currentSector = pill.dataset.sector;
            currentPage = 1;
            render();
        });
    });
}
buildSectorPills();

// ---- Search with Dropdown ----
const searchInput = document.getElementById('searchInput');
const searchDropdown = document.getElementById('searchDropdown');
const searchShortcut = document.getElementById('searchShortcut');
let searchActiveIdx = -1;

function searchStocks(query) {
    if (!query || query.length === 0) return [];
    const q = query.toLowerCase();

    // Score each stock for relevance
    const scored = SP500_STOCKS.map(s => {
        const name = s.name.toLowerCase();
        const ticker = s.ticker.toLowerCase();
        const sector = s.sector.toLowerCase();
        let score = 0;

        // Exact ticker match = highest
        if (ticker === q) score = 100;
        // Ticker starts with query
        else if (ticker.startsWith(q)) score = 80;
        // Ticker contains query
        else if (ticker.includes(q)) score = 60;
        // Name starts with query
        else if (name.startsWith(q)) score = 70;
        // Name word starts with query (e.g. "mic" matches "Micron" and "Microsoft")
        else if (name.split(/\s+/).some(w => w.startsWith(q))) score = 55;
        // Name contains query anywhere
        else if (name.includes(q)) score = 40;
        // Sector match
        else if (sector.includes(q)) score = 20;

        // Tiebreak: higher market cap ranks higher
        if (score > 0) score += s.marketCap / 1e14;

        return { stock: s, score };
    })
    .filter(r => r.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, 8);

    return scored.map(r => r.stock);
}

function highlightMatch(text, query) {
    const idx = text.toLowerCase().indexOf(query.toLowerCase());
    if (idx === -1) return text;
    return text.substring(0, idx) + '<mark>' + text.substring(idx, idx + query.length) + '</mark>' + text.substring(idx + query.length);
}

function renderDropdown(query) {
    const results = searchStocks(query);
    searchActiveIdx = -1;

    if (!query || query.length === 0) {
        searchDropdown.classList.remove('open');
        return;
    }

    if (results.length === 0) {
        searchDropdown.innerHTML = '<div class="search-no-results">No stocks found for "' + query + '"</div>';
        searchDropdown.classList.add('open');
        return;
    }

    let html = '<div class="search-dropdown-header">Stocks</div>';
    results.forEach((stock, i) => {
        const logoUrl = 'https://www.google.com/s2/favicons?domain=' + stock.domain + '&sz=128';
        const chgCls = stock.change1d >= 0 ? 'change-up' : 'change-down';
        const chgSign = stock.change1d >= 0 ? '+' : '';
        html += `
            <div class="search-result" data-idx="${i}" data-ticker="${stock.ticker}">
                <img class="search-result-logo" src="${logoUrl}" alt="${stock.ticker}"
                     onerror="this.style.display='none';this.nextElementSibling.style.display='flex';">
                <div class="search-result-icon" style="background:${stock.color};display:none">${stock.ticker.substring(0, 2)}</div>
                <div class="search-result-info">
                    <div class="search-result-name">${highlightMatch(stock.name, query)} <span style="color:var(--text-secondary);font-weight:400;font-size:12px">${stock.ticker}</span></div>
                    <div class="search-result-sub">${stock.sector} · Rank #${stock.rank}</div>
                </div>
                <div class="search-result-price">
                    <div class="search-result-price-val">${formatPrice(stock.price)}</div>
                    <div class="search-result-price-chg ${chgCls}">${chgSign}${stock.change1d.toFixed(2)}%</div>
                </div>
            </div>`;
    });
    searchDropdown.innerHTML = html;
    searchDropdown.classList.add('open');

    // Click handlers on results
    searchDropdown.querySelectorAll('.search-result').forEach(el => {
        el.addEventListener('click', () => {
            const stock = SP500_STOCKS.find(s => s.ticker === el.dataset.ticker);
            if (stock) {
                searchDropdown.classList.remove('open');
                searchInput.value = '';
                searchTerm = '';
                openDetail(stock);
            }
        });
    });
}

searchInput.addEventListener('input', (e) => {
    const q = e.target.value.trim();
    searchTerm = q;

    // Clear sector filter when searching
    if (q.length > 0 && currentSector !== 'all') {
        currentSector = 'all';
        document.querySelectorAll('.pill').forEach(p => {
            p.classList.toggle('active', p.dataset.sector === 'all');
        });
    }

    // Switch to stocks view if on sectors
    if (currentView === 'sectors' && q.length > 0) {
        currentView = 'stocks';
        document.getElementById('tableView').style.display = '';
        document.getElementById('sectorsView').style.display = 'none';
        document.querySelector('.pagination').style.display = '';
        document.querySelector('.sector-pills').style.display = '';
        document.querySelectorAll('.nav a').forEach(a => a.classList.toggle('nav-active', a.dataset.view === 'stocks'));
    }

    renderDropdown(q);
    currentPage = 1;
    render();
});

searchInput.addEventListener('focus', () => {
    if (searchInput.value.trim().length > 0) {
        renderDropdown(searchInput.value.trim());
    }
    searchShortcut.style.display = 'none';
});

searchInput.addEventListener('blur', () => {
    // Delay to allow click on dropdown
    setTimeout(() => {
        searchDropdown.classList.remove('open');
        if (searchInput.value.trim().length === 0) {
            searchShortcut.style.display = '';
        }
    }, 200);
});

// Keyboard navigation in dropdown
searchInput.addEventListener('keydown', (e) => {
    const items = searchDropdown.querySelectorAll('.search-result');
    if (!items.length) return;

    if (e.key === 'ArrowDown') {
        e.preventDefault();
        searchActiveIdx = Math.min(searchActiveIdx + 1, items.length - 1);
        items.forEach((el, i) => el.classList.toggle('active', i === searchActiveIdx));
    } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        searchActiveIdx = Math.max(searchActiveIdx - 1, 0);
        items.forEach((el, i) => el.classList.toggle('active', i === searchActiveIdx));
    } else if (e.key === 'Enter' && searchActiveIdx >= 0) {
        e.preventDefault();
        items[searchActiveIdx].click();
    } else if (e.key === 'Escape') {
        searchDropdown.classList.remove('open');
        searchInput.blur();
    }
});

// "/" shortcut to focus search
document.addEventListener('keydown', (e) => {
    if (e.key === '/' && document.activeElement !== searchInput && !e.ctrlKey && !e.metaKey) {
        e.preventDefault();
        searchInput.focus();
    }
});

// Event: Pagination
document.getElementById('prevPage').addEventListener('click', () => {
    if (currentPage > 1) { currentPage--; render(); }
});
document.getElementById('nextPage').addEventListener('click', () => {
    const data = getFilteredData();
    const totalPages = Math.ceil(data.length / perPage);
    if (currentPage < totalPages) { currentPage++; render(); }
});

// ---- Stock Detail Panel ----

function getStockDescription(stock) {
    if (typeof STOCK_DESCRIPTIONS_DATA !== 'undefined' && STOCK_DESCRIPTIONS_DATA[stock.ticker]) {
        return STOCK_DESCRIPTIONS_DATA[stock.ticker];
    }
    return `${stock.name} (${stock.ticker}) is a ${stock.sector} company listed on the S&P 500 with a market capitalization of ${formatCurrency(stock.marketCap)}. The stock is currently trading at ${formatPrice(stock.price)} per share.`;
}

function generateStockChartData(stock, days) {
    let seed = 0;
    for (let i = 0; i < stock.ticker.length; i++) seed += stock.ticker.charCodeAt(i) * (i + 1);
    seed += days;
    function rand() {
        seed = (seed * 16807) % 2147483647;
        return (seed & 0x7fffffff) / 0x7fffffff;
    }
    const data = [];
    const endPrice = stock.price;
    const vol = 0.012;
    const drift = stock.change7d > 0 ? 0.0004 : -0.0003;
    let prices = [endPrice];
    for (let i = 1; i < days; i++) {
        const prev = prices[i - 1];
        prices.push(prev + prev * ((rand() - 0.5) * 2 * vol - drift));
    }
    prices.reverse();
    const now = new Date();
    for (let i = 0; i < prices.length; i++) {
        const d = new Date(now);
        d.setDate(d.getDate() - (prices.length - 1 - i));
        data.push({ date: d, price: prices[i] });
    }
    return data;
}

function renderDetailChart(stock, days) {
    const container = document.querySelector('.detail-chart-area');
    if (!container) return;
    const data = generateStockChartData(stock, days);

    const w = container.clientWidth || 580;
    const h = container.clientHeight || 220;
    const padTop = 10, padBottom = 24, padLeft = 55, padRight = 10;
    const chartW = w - padLeft - padRight;
    const chartH = h - padTop - padBottom;

    const prices = data.map(d => d.price);
    const minP = Math.min(...prices);
    const maxP = Math.max(...prices);
    const range = maxP - minP || 1;
    const isUp = prices[prices.length - 1] >= prices[0];
    const color = isUp ? '#16c784' : '#ea3943';

    const points = data.map((d, i) => ({
        x: padLeft + (i / (data.length - 1)) * chartW,
        y: padTop + (1 - (d.price - minP) / range) * chartH,
    }));
    let pathD = points.map((p, i) => (i === 0 ? `M${p.x},${p.y}` : ` L${p.x},${p.y}`)).join('');
    const fillD = pathD + ` L${points[points.length - 1].x},${padTop + chartH} L${padLeft},${padTop + chartH} Z`;

    let yLabels = '', gridLines = '';
    for (let i = 0; i <= 4; i++) {
        const val = minP + (range * i / 4);
        const y = padTop + (1 - i / 4) * chartH;
        yLabels += `<text x="${padLeft - 8}" y="${y + 4}" text-anchor="end" fill="#9ca3af" font-size="11" font-family="system-ui">$${val.toFixed(0)}</text>`;
        gridLines += `<line x1="${padLeft}" y1="${y}" x2="${w - padRight}" y2="${y}" stroke="#f3f4f6" stroke-width="1"/>`;
    }
    let xLabels = '';
    const lc = Math.min(6, data.length);
    for (let i = 0; i < lc; i++) {
        const idx = Math.round(i * (data.length - 1) / (lc - 1));
        const d = data[idx].date;
        const x = points[idx].x;
        const label = days <= 30
            ? `${d.getMonth() + 1}/${d.getDate()}`
            : d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        xLabels += `<text x="${x}" y="${h - 4}" text-anchor="middle" fill="#9ca3af" font-size="10" font-family="system-ui">${label}</text>`;
    }
    const lastP = points[points.length - 1];

    container.innerHTML = `
        <svg viewBox="0 0 ${w} ${h}" xmlns="http://www.w3.org/2000/svg">
            <defs>
                <linearGradient id="detailGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stop-color="${color}" stop-opacity="0.2"/>
                    <stop offset="100%" stop-color="${color}" stop-opacity="0.01"/>
                </linearGradient>
            </defs>
            ${gridLines}${yLabels}${xLabels}
            <path d="${fillD}" fill="url(#detailGrad)"/>
            <path d="${pathD}" fill="none" stroke="${color}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
            <circle cx="${lastP.x}" cy="${lastP.y}" r="4.5" fill="${color}"/>
            <circle cx="${lastP.x}" cy="${lastP.y}" r="8" fill="${color}" opacity="0.15"/>
        </svg>
    `;
}

function openDetail(stock) {
    const panel = document.getElementById('detailPanel');
    const overlay = document.getElementById('detailOverlay');
    const content = document.getElementById('detailContent');
    const logoUrl = `https://www.google.com/s2/favicons?domain=${stock.domain}&sz=128`;

    // 52W range calc (simulated)
    const high52 = stock.price * (1 + Math.abs(stock.changeYtd) / 100 + 0.12);
    const low52 = stock.price * (1 - Math.abs(stock.changeYtd) / 100 - 0.08);
    const rangePct = ((stock.price - low52) / (high52 - low52)) * 100;

    // Simulated extra stats
    const eps = stock.pe ? (stock.price / stock.pe).toFixed(2) : '—';
    const divYield = stock.sector === 'Technology' ? (Math.random() * 1.2).toFixed(2)
        : stock.sector === 'Utilities' ? (2.5 + Math.random() * 2).toFixed(2)
        : (0.5 + Math.random() * 2.5).toFixed(2);
    const beta = (0.6 + Math.random() * 1.2).toFixed(2);

    // Find sector peers
    const peers = SP500_STOCKS.filter(s => s.sector === stock.sector && s.ticker !== stock.ticker).slice(0, 6);

    content.innerHTML = `
        <div class="detail-header">
            <img class="detail-logo" src="${logoUrl}" alt="${stock.ticker}"
                 onerror="this.style.display='none';this.nextElementSibling.style.display='flex';">
            <div class="detail-icon" style="background:${stock.color};display:none">${stock.ticker.substring(0, 2)}</div>
            <div class="detail-title-group">
                <div class="detail-name">${stock.name}</div>
                <div class="detail-ticker-row">
                    <span class="detail-ticker">${stock.ticker}</span>
                    <span class="detail-sector-badge">${stock.sector}</span>
                </div>
            </div>
            <button class="detail-close" id="detailClose">&times;</button>
        </div>

        <div class="detail-price-row">
            <span class="detail-price">${formatPrice(stock.price)}</span>
            <span class="detail-price-change ${stock.change1d >= 0 ? 'change-up' : 'change-down'}">${stock.change1d >= 0 ? '+' : ''}${stock.change1d.toFixed(2)}%</span>
        </div>

        <div class="detail-chart-wrap">
            <div class="detail-chart-periods">
                <button class="chart-period" data-d="7">1W</button>
                <button class="chart-period active" data-d="30">1M</button>
                <button class="chart-period" data-d="90">3M</button>
                <button class="chart-period" data-d="180">6M</button>
                <button class="chart-period" data-d="365">1Y</button>
            </div>
            <div class="detail-chart-area"></div>
        </div>

        <div class="detail-stats">
            <div class="detail-stat-item">
                <span class="detail-stat-label">Market Cap</span>
                <span class="detail-stat-value">${formatCurrency(stock.marketCap)}</span>
            </div>
            <div class="detail-stat-item">
                <span class="detail-stat-label">Volume (24h)</span>
                <span class="detail-stat-value">${formatVolume(stock.volume)}</span>
            </div>
            <div class="detail-stat-item">
                <span class="detail-stat-label">P/E Ratio</span>
                <span class="detail-stat-value">${stock.pe ? stock.pe.toFixed(1) : '—'}</span>
            </div>
            <div class="detail-stat-item">
                <span class="detail-stat-label">EPS</span>
                <span class="detail-stat-value">${eps !== '—' ? '$' + eps : '—'}</span>
            </div>
            <div class="detail-stat-item">
                <span class="detail-stat-label">Dividend Yield</span>
                <span class="detail-stat-value">${divYield}%</span>
            </div>
            <div class="detail-stat-item">
                <span class="detail-stat-label">Beta</span>
                <span class="detail-stat-value">${beta}</span>
            </div>
            <div class="detail-stat-item">
                <span class="detail-stat-label">7d Change</span>
                <span class="detail-stat-value ${stock.change7d >= 0 ? 'change-up' : 'change-down'}">${stock.change7d >= 0 ? '+' : ''}${stock.change7d.toFixed(2)}%</span>
            </div>
            <div class="detail-stat-item">
                <span class="detail-stat-label">YTD Change</span>
                <span class="detail-stat-value ${stock.changeYtd >= 0 ? 'change-up' : 'change-down'}">${stock.changeYtd >= 0 ? '+' : ''}${stock.changeYtd.toFixed(2)}%</span>
            </div>
            <div class="range-bar-wrap">
                <div class="range-bar-label">
                    <span>52W Low: $${low52.toFixed(2)}</span>
                    <span>52W High: $${high52.toFixed(2)}</span>
                </div>
                <div class="range-bar">
                    <div class="range-bar-fill" style="width:${rangePct.toFixed(1)}%"></div>
                    <div class="range-bar-dot" style="left:${rangePct.toFixed(1)}%"></div>
                </div>
            </div>
        </div>

        <a href="s/${stock.ticker.toLowerCase().replace('.', '-')}.html" class="detail-full-link">View full ${stock.ticker} page &rarr;</a>

        <div class="detail-about">
            <div class="detail-about-title">About ${stock.name}</div>
            <div class="detail-about-text">${getStockDescription(stock)}</div>
        </div>

        <div class="detail-peers">
            <div class="detail-peers-title">Sector Peers — ${stock.sector}</div>
            <div class="detail-peers-list">
                ${peers.map(p => `
                    <div class="peer-chip" data-ticker="${p.ticker}">
                        <span class="peer-chip-ticker">${p.ticker}</span>
                        <span class="peer-chip-change ${p.change1d >= 0 ? 'change-up' : 'change-down'}">${p.change1d >= 0 ? '+' : ''}${p.change1d.toFixed(2)}%</span>
                    </div>
                `).join('')}
            </div>
        </div>
    `;

    // Open panel
    panel.classList.add('open');
    overlay.classList.add('open');
    document.body.style.overflow = 'hidden';

    // Render chart after DOM is ready
    requestAnimationFrame(() => renderDetailChart(stock, 30));

    // Chart period buttons
    content.querySelectorAll('.detail-chart-periods .chart-period').forEach(btn => {
        btn.addEventListener('click', () => {
            content.querySelectorAll('.detail-chart-periods .chart-period').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            renderDetailChart(stock, parseInt(btn.dataset.d));
        });
    });

    // Close
    document.getElementById('detailClose').addEventListener('click', closeDetail);
    overlay.addEventListener('click', closeDetail);

    // Peer chips — click to open that stock
    content.querySelectorAll('.peer-chip').forEach(chip => {
        chip.addEventListener('click', () => {
            const peer = SP500_STOCKS.find(s => s.ticker === chip.dataset.ticker);
            if (peer) openDetail(peer);
        });
    });
}

function closeDetail() {
    document.getElementById('detailPanel').classList.remove('open');
    document.getElementById('detailOverlay').classList.remove('open');
    document.body.style.overflow = '';
}

// Close on Escape
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeDetail();
});

// ---- S&P 500 Index Chart ----

function generateIndexData(days) {
    const data = [];
    let seed = 42;
    function rand() {
        seed = (seed * 16807) % 2147483647;
        return (seed & 0x7fffffff) / 0x7fffffff;
    }

    // Use real index price from MARKET_SUMMARY if available
    const ms = typeof MARKET_SUMMARY !== 'undefined' ? MARKET_SUMMARY : null;
    const endPrice = (ms && ms.index) ? ms.index.price : 5954.50;
    const dailyVol = 0.008;
    const drift = (ms && ms.index && ms.index.changePct >= 0) ? 0.0003 : -0.0003;

    // Generate forward then reverse so end = current price
    let prices = [endPrice];
    for (let i = 1; i < days; i++) {
        const prev = prices[i - 1];
        const change = prev * ((rand() - 0.5) * 2 * dailyVol - drift);
        prices.push(prev + change);
    }
    prices.reverse();

    // Build with dates
    const now = new Date();
    for (let i = 0; i < prices.length; i++) {
        const d = new Date(now);
        d.setDate(d.getDate() - (prices.length - 1 - i));
        data.push({ date: d, price: prices[i] });
    }
    return data;
}

function renderIndexChart(days) {
    const container = document.getElementById('indexChart');
    const data = generateIndexData(days);

    const w = container.clientWidth || 600;
    const h = container.clientHeight || 180;
    const padTop = 10, padBottom = 24, padLeft = 50, padRight = 10;
    const chartW = w - padLeft - padRight;
    const chartH = h - padTop - padBottom;

    const prices = data.map(d => d.price);
    const minP = Math.min(...prices);
    const maxP = Math.max(...prices);
    const range = maxP - minP || 1;

    const isUp = prices[prices.length - 1] >= prices[0];
    const color = isUp ? '#16c784' : '#ea3943';

    // Build path
    let pathD = '';
    const points = data.map((d, i) => {
        const x = padLeft + (i / (data.length - 1)) * chartW;
        const y = padTop + (1 - (d.price - minP) / range) * chartH;
        return { x, y };
    });
    points.forEach((p, i) => {
        pathD += i === 0 ? `M${p.x},${p.y}` : ` L${p.x},${p.y}`;
    });

    const fillD = pathD + ` L${points[points.length - 1].x},${padTop + chartH} L${padLeft},${padTop + chartH} Z`;

    // Y-axis labels (5 ticks)
    let yLabels = '';
    let gridLines = '';
    for (let i = 0; i <= 4; i++) {
        const val = minP + (range * i / 4);
        const y = padTop + (1 - i / 4) * chartH;
        yLabels += `<text x="${padLeft - 8}" y="${y + 4}" text-anchor="end" fill="#9ca3af" font-size="11" font-family="system-ui">${val.toFixed(0)}</text>`;
        gridLines += `<line x1="${padLeft}" y1="${y}" x2="${w - padRight}" y2="${y}" stroke="#f3f4f6" stroke-width="1"/>`;
    }

    // X-axis labels
    let xLabels = '';
    const labelCount = Math.min(6, data.length);
    for (let i = 0; i < labelCount; i++) {
        const idx = Math.round(i * (data.length - 1) / (labelCount - 1));
        const d = data[idx].date;
        const x = points[idx].x;
        const label = days <= 30
            ? `${d.getMonth() + 1}/${d.getDate()}`
            : d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        xLabels += `<text x="${x}" y="${h - 4}" text-anchor="middle" fill="#9ca3af" font-size="10" font-family="system-ui">${label}</text>`;
    }

    // Current price dot
    const lastP = points[points.length - 1];

    container.innerHTML = `
        <svg viewBox="0 0 ${w} ${h}" xmlns="http://www.w3.org/2000/svg">
            <defs>
                <linearGradient id="indexGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stop-color="${color}" stop-opacity="0.2"/>
                    <stop offset="100%" stop-color="${color}" stop-opacity="0.01"/>
                </linearGradient>
            </defs>
            ${gridLines}
            ${yLabels}
            ${xLabels}
            <path d="${fillD}" fill="url(#indexGrad)"/>
            <path d="${pathD}" fill="none" stroke="${color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <circle cx="${lastP.x}" cy="${lastP.y}" r="4" fill="${color}"/>
            <circle cx="${lastP.x}" cy="${lastP.y}" r="7" fill="${color}" opacity="0.2"/>
        </svg>
    `;
}

// Period buttons
let currentChartDays = 30;
document.querySelectorAll('.chart-period').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.chart-period').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        currentChartDays = parseInt(btn.dataset.days);
        renderIndexChart(currentChartDays);
    });
});

// Redraw on resize
window.addEventListener('resize', () => renderIndexChart(currentChartDays));

// ---- Trending Bar ----
function renderTrending() {
    const bar = document.getElementById('trendingBar');
    const sorted = [...SP500_STOCKS].sort((a, b) => b.change1d - a.change1d);
    const gainers = sorted.slice(0, 5);
    const losers = sorted.slice(-5).reverse();

    function makeItem(stock, rank, label) {
        const cls = stock.change1d >= 0 ? 'change-up' : 'change-down';
        const sign = stock.change1d >= 0 ? '+' : '';
        const logo = `https://www.google.com/s2/favicons?domain=${stock.domain}&sz=64`;
        return `
            <div class="trending-item" data-ticker="${stock.ticker}">
                <span class="trending-rank">${rank}</span>
                <img class="trending-logo" src="${logo}" alt="${stock.ticker}" onerror="this.style.display='none'">
                <span class="trending-name">${stock.ticker}</span>
                <span class="trending-price">${formatPrice(stock.price)}</span>
                <span class="trending-change ${cls}">${sign}${stock.change1d.toFixed(2)}%</span>
            </div>`;
    }

    let html = '<div class="trending-divider">&#x1F525; Top Gainers</div>';
    gainers.forEach((s, i) => { html += makeItem(s, i + 1, 'gainer'); });
    html += '<div class="trending-divider">&#x1F534; Top Losers</div>';
    losers.forEach((s, i) => { html += makeItem(s, i + 1, 'loser'); });

    // Duplicate for seamless scroll
    bar.innerHTML = html + html;

    // Click to open detail
    bar.querySelectorAll('.trending-item').forEach(el => {
        el.addEventListener('click', () => {
            const stock = SP500_STOCKS.find(s => s.ticker === el.dataset.ticker);
            if (stock) openDetail(stock);
        });
    });
}
renderTrending();

// ---- Dynamic Stats ----
function updateStats() {
    const ms = typeof MARKET_SUMMARY !== 'undefined' ? MARKET_SUMMARY : null;
    const totalMcap = ms ? ms.totalMarketCap : SP500_STOCKS.reduce((s, st) => s + st.marketCap, 0);
    const totalVol = ms ? ms.totalVolume : SP500_STOCKS.reduce((s, st) => s + st.volume, 0);
    const advancing = ms ? ms.advancing : SP500_STOCKS.filter(s => s.change1d > 0).length;
    const declining = ms ? ms.declining : SP500_STOCKS.filter(s => s.change1d < 0).length;
    const total = SP500_STOCKS.length;

    // Top bar
    document.getElementById('stockCount').textContent = total;
    document.getElementById('totalMarketCap').textContent = formatCurrency(totalMcap);
    document.getElementById('totalVolume').textContent = formatVolume(totalVol);

    // S&P 500 index in top bar
    if (ms && ms.index) {
        const idx = ms.index;
        document.getElementById('spIndex').textContent = idx.price.toLocaleString('en-US', {minimumFractionDigits: 2});
        const spChgEl = document.getElementById('spIndex').nextElementSibling;
        if (spChgEl) {
            spChgEl.className = idx.changePct >= 0 ? 'change-up' : 'change-down';
            spChgEl.textContent = (idx.changePct >= 0 ? '+' : '') + idx.changePct.toFixed(2) + '%';
        }
    }

    // Hero chart stats
    if (ms && ms.index) {
        const idx = ms.index;
        const fmt = n => n.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2});
        document.getElementById('heroPrice').textContent = fmt(idx.price);
        const heroChg = document.getElementById('heroChange');
        const chgCls = idx.changePct >= 0 ? 'change-up' : 'change-down';
        const chgSign = idx.changePct >= 0 ? '+' : '';
        heroChg.className = 'index-hero-change ' + chgCls;
        heroChg.innerHTML = chgSign + idx.change.toFixed(2) + ' (' + chgSign + idx.changePct.toFixed(2) + '%) <span class="index-hero-asof">Today</span>';
        document.getElementById('heroOpen').textContent = fmt(idx.open);
        document.getElementById('heroHigh').textContent = fmt(idx.high);
        document.getElementById('heroLow').textContent = fmt(idx.low);
        document.getElementById('hero52H').textContent = fmt(idx.high52);
        document.getElementById('hero52L').textContent = fmt(idx.low52);
        const ytdEl = document.getElementById('heroYtd');
        ytdEl.className = 'index-stat-val ' + (idx.ytd >= 0 ? 'change-up' : 'change-down');
        ytdEl.textContent = (idx.ytd >= 0 ? '+' : '') + idx.ytd.toFixed(2) + '%';
    }

    // Summary cards
    document.getElementById('cardFearGreed').textContent = ms ? ms.fearGreed : '—';
    document.getElementById('cardFearGreedLabel').textContent = ms ? ms.fearGreedLabel : '—';
    document.getElementById('cardAdvancing').textContent = advancing;
    document.getElementById('cardAdvancingPct').textContent = Math.round(advancing / total * 100) + '% of stocks';
    document.getElementById('cardDeclining').textContent = declining;
    document.getElementById('cardDecliningPct').textContent = Math.round(declining / total * 100) + '% of stocks';
    document.getElementById('card52H').textContent = ms ? ms.high52Count : '—';
    document.getElementById('cardMcap').textContent = formatCurrency(totalMcap);

    // Last updated timestamp
    if (typeof DATA_LAST_UPDATED !== 'undefined') {
        const d = new Date(DATA_LAST_UPDATED);
        const now = new Date();
        const diffMin = Math.round((now - d) / 60000);
        let ago;
        if (diffMin < 1) ago = 'just now';
        else if (diffMin < 60) ago = diffMin + 'm ago';
        else if (diffMin < 1440) ago = Math.round(diffMin / 60) + 'h ago';
        else ago = Math.round(diffMin / 1440) + 'd ago';
        document.getElementById('lastUpdated').textContent = 'Updated ' + ago;
    }
}
updateStats();

// ---- Email Subscribe Form ----
const subForm = document.getElementById('subscribeForm');
if (subForm) {
    subForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const email = document.getElementById('subEmail').value.trim();
        const btn = document.getElementById('subBtn');
        const msg = document.getElementById('subMsg');

        if (!email) return;

        btn.disabled = true;
        btn.textContent = 'Subscribing...';
        msg.textContent = '';
        msg.className = 'subscribe-msg';

        try {
            const res = await fetch('/.netlify/functions/subscribe', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email }),
            });
            const data = await res.json();

            if (res.ok) {
                msg.textContent = 'Subscribed! Check your inbox for tomorrow\'s market brief.';
                msg.className = 'subscribe-msg success';
                document.getElementById('subEmail').value = '';
            } else {
                msg.textContent = data.error || 'Something went wrong. Try again.';
                msg.className = 'subscribe-msg error';
            }
        } catch {
            msg.textContent = 'Network error. Please try again.';
            msg.className = 'subscribe-msg error';
        }

        btn.disabled = false;
        btn.textContent = 'Subscribe';
    });
}

// Initial render
renderIndexChart(currentChartDays);
render();
