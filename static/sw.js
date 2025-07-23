/**
 * McMaster-Carr Style Service Worker
 * Implements aggressive caching for instant repeat visits
 */

const CACHE_NAME = 'gym-app-v1';
const STATIC_CACHE_NAME = 'gym-static-v1';
const DYNAMIC_CACHE_NAME = 'gym-dynamic-v1';

// Static assets to cache immediately
const STATIC_ASSETS = [
    '/',
    '/index.html',
    '/login.html',
    '/register.html',
    '/profile.html',
    '/mobile.html',
    '/src/output.css',
    '/src/device-detection.js',
    '/src/prefetch.js'
];

// API endpoints to cache
const API_CACHE_PATTERNS = [
    /^\/api\/leaderboard/,
    /^\/api\/team_leaderboard/,
    /^\/api\/videos/,
    /^\/api\/user\/.*\/progress/
];

// Cache strategies
const CACHE_STRATEGIES = {
    CACHE_FIRST: 'cache-first',
    NETWORK_FIRST: 'network-first',
    STALE_WHILE_REVALIDATE: 'stale-while-revalidate'
};

self.addEventListener('install', (event) => {
    console.log('🔧 Service Worker installing...');
    
    event.waitUntil(
        Promise.all([
            // Cache static assets
            caches.open(STATIC_CACHE_NAME).then((cache) => {
                console.log('📦 Caching static assets');
                return cache.addAll(STATIC_ASSETS);
            }),
            // Skip waiting to activate immediately
            self.skipWaiting()
        ])
    );
});

self.addEventListener('activate', (event) => {
    console.log('✅ Service Worker activated');
    
    event.waitUntil(
        Promise.all([
            // Clean up old caches
            cleanupOldCaches(),
            // Take control of all clients immediately
            self.clients.claim()
        ])
    );
});

self.addEventListener('fetch', (event) => {
    const { request } = event;
    const url = new URL(request.url);
    
    // Skip non-GET requests and external URLs
    if (request.method !== 'GET' || url.origin !== location.origin) {
        return;
    }

    // Handle different resource types with appropriate strategies
    if (isStaticAsset(url)) {
        event.respondWith(handleStaticAsset(request));
    } else if (isAPIRequest(url)) {
        event.respondWith(handleAPIRequest(request));
    } else if (isHTMLPage(url)) {
        event.respondWith(handleHTMLPage(request));
    } else {
        event.respondWith(handleDefault(request));
    }
});

/**
 * Handle static assets with cache-first strategy
 */
async function handleStaticAsset(request) {
    try {
        const cached = await caches.match(request);
        if (cached) {
            console.log(`📋 Cache hit: ${request.url}`);
            return cached;
        }

        const response = await fetch(request);
        if (response.ok) {
            const cache = await caches.open(STATIC_CACHE_NAME);
            cache.put(request, response.clone());
            console.log(`💾 Cached: ${request.url}`);
        }
        return response;
    } catch (error) {
        console.error('Static asset fetch failed:', error);
        return caches.match(request) || new Response('Asset not available', { status: 404 });
    }
}

/**
 * Handle API requests with network-first strategy and intelligent caching
 */
async function handleAPIRequest(request) {
    const url = new URL(request.url);
    
    try {
        // Try network first for fresh data
        const response = await fetch(request);
        
        if (response.ok) {
            // Cache successful API responses
            const cache = await caches.open(DYNAMIC_CACHE_NAME);
            
            // Set cache TTL based on endpoint
            const ttl = getAPITTL(url.pathname);
            const responseToCache = response.clone();
            
            // Add timestamp for TTL checking
            const headers = new Headers(responseToCache.headers);
            headers.set('sw-cached-at', Date.now().toString());
            headers.set('sw-ttl', ttl.toString());
            
            const cachedResponse = new Response(responseToCache.body, {
                status: responseToCache.status,
                statusText: responseToCache.statusText,
                headers: headers
            });
            
            cache.put(request, cachedResponse);
            console.log(`🌐 API cached: ${request.url} (TTL: ${ttl}ms)`);
        }
        
        return response;
    } catch (error) {
        console.warn('Network failed, trying cache:', error);
        
        // Fallback to cache
        const cached = await caches.match(request);
        if (cached && isCacheValid(cached)) {
            console.log(`📋 API cache fallback: ${request.url}`);
            return cached;
        }
        
        throw error;
    }
}

/**
 * Handle HTML pages with stale-while-revalidate strategy
 */
async function handleHTMLPage(request) {
    const cached = await caches.match(request);
    
    // Return cached version immediately if available
    const responsePromise = cached || fetch(request);
    
    // Update cache in background if stale
    if (cached && shouldRevalidate(cached)) {
        console.log(`🔄 Revalidating: ${request.url}`);
        fetch(request).then(response => {
            if (response.ok) {
                const cache = caches.open(DYNAMIC_CACHE_NAME);
                cache.then(c => c.put(request, response.clone()));
            }
        }).catch(err => console.warn('Background revalidation failed:', err));
    }
    
    try {
        const response = await responsePromise;
        
        // Cache new HTML pages
        if (!cached && response.ok) {
            const cache = await caches.open(DYNAMIC_CACHE_NAME);
            cache.put(request, response.clone());
            console.log(`💾 HTML cached: ${request.url}`);
        }
        
        return response;
    } catch (error) {
        console.error('HTML fetch failed:', error);
        return cached || new Response('Page not available offline', { 
            status: 503,
            headers: { 'Content-Type': 'text/html' }
        });
    }
}

/**
 * Default handler for other requests
 */
async function handleDefault(request) {
    try {
        return await fetch(request);
    } catch (error) {
        const cached = await caches.match(request);
        return cached || new Response('Resource not available', { status: 404 });
    }
}

/**
 * Check if URL is a static asset
 */
function isStaticAsset(url) {
    return /\.(css|js|png|jpg|jpeg|gif|svg|ico|woff|woff2|ttf|mp4)$/i.test(url.pathname) ||
           url.pathname.includes('/src/') ||
           url.pathname.includes('/uploads/');
}

/**
 * Check if URL is an API request
 */
function isAPIRequest(url) {
    return url.pathname.startsWith('/api/');
}

/**
 * Check if URL is an HTML page
 */
function isHTMLPage(url) {
    return url.pathname.endsWith('.html') || url.pathname === '/';
}

/**
 * Get TTL for API endpoints based on data freshness requirements
 */
function getAPITTL(pathname) {
    if (pathname.includes('/leaderboard')) return 300000; // 5 minutes
    if (pathname.includes('/videos')) return 60000; // 1 minute
    if (pathname.includes('/progress')) return 600000; // 10 minutes
    if (pathname.includes('/profile')) return 1800000; // 30 minutes
    return 300000; // Default 5 minutes
}

/**
 * Check if cached response is still valid
 */
function isCacheValid(response) {
    const cachedAt = response.headers.get('sw-cached-at');
    const ttl = response.headers.get('sw-ttl');
    
    if (!cachedAt || !ttl) return true; // No TTL, assume valid
    
    const age = Date.now() - parseInt(cachedAt);
    return age < parseInt(ttl);
}

/**
 * Check if cached HTML should be revalidated
 */
function shouldRevalidate(response) {
    const cachedAt = response.headers.get('sw-cached-at');
    if (!cachedAt) return true;
    
    const age = Date.now() - parseInt(cachedAt);
    return age > 60000; // Revalidate if older than 1 minute
}

/**
 * Clean up old cache versions
 */
async function cleanupOldCaches() {
    const cacheNames = await caches.keys();
    const currentCaches = [STATIC_CACHE_NAME, DYNAMIC_CACHE_NAME];
    
    const deletePromises = cacheNames
        .filter(cacheName => !currentCaches.includes(cacheName))
        .map(cacheName => {
            console.log(`🗑️ Deleting old cache: ${cacheName}`);
            return caches.delete(cacheName);
        });
    
    return Promise.all(deletePromises);
}

// Handle messages from main thread
self.addEventListener('message', (event) => {
    if (event.data && event.data.type === 'SKIP_WAITING') {
        self.skipWaiting();
    } else if (event.data && event.data.type === 'CLEAR_CACHE') {
        event.waitUntil(clearAllCaches());
        event.ports[0].postMessage({ success: true });
    }
});

/**
 * Clear all caches (for debugging/admin purposes)
 */
async function clearAllCaches() {
    const cacheNames = await caches.keys();
    const deletePromises = cacheNames.map(name => caches.delete(name));
    await Promise.all(deletePromises);
    console.log('🧹 All caches cleared');
}