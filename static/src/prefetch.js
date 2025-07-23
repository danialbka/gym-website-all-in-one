/**
 * McMaster-Carr Style Prefetching System
 * Implements hover-based prefetching and pushState navigation
 */

class PrefetchManager {
    constructor() {
        this.prefetchCache = new Map();
        this.hoverTimeouts = new Map();
        this.prefetchedUrls = new Set();
        this.hoverDelay = 65; // McMaster uses ~65ms hover delay
        this.init();
    }

    init() {
        this.setupHoverPrefetch();
        this.setupPushStateNavigation();
        this.preloadCriticalPages();
    }

    /**
     * Setup hover-based prefetching for all internal links
     */
    setupHoverPrefetch() {
        document.addEventListener('mouseover', (e) => {
            const link = e.target.closest('a[href]');
            if (!link || !this.isInternalLink(link.href)) return;

            const url = link.href;
            
            // Set timeout to prefetch after hover delay
            const timeoutId = setTimeout(() => {
                this.prefetchPage(url);
            }, this.hoverDelay);
            
            this.hoverTimeouts.set(link, timeoutId);
        });

        document.addEventListener('mouseout', (e) => {
            const link = e.target.closest('a[href]');
            if (!link) return;

            // Cancel prefetch if user stops hovering quickly
            const timeoutId = this.hoverTimeouts.get(link);
            if (timeoutId) {
                clearTimeout(timeoutId);
                this.hoverTimeouts.delete(link);
            }
        });
    }

    /**
     * Setup pushState navigation for seamless page transitions
     */
    setupPushStateNavigation() {
        document.addEventListener('click', (e) => {
            const link = e.target.closest('a[href]');
            if (!link || !this.isInternalLink(link.href)) return;
            
            // Don't intercept external links, downloads, or special cases
            if (link.target === '_blank' || 
                link.download || 
                e.metaKey || 
                e.ctrlKey || 
                e.shiftKey) return;

            e.preventDefault();
            this.navigateWithPushState(link.href);
        });

        // Handle browser back/forward buttons
        window.addEventListener('popstate', (e) => {
            if (e.state && e.state.prefetched) {
                this.loadCachedPage(window.location.href);
            } else {
                window.location.reload();
            }
        });
    }

    /**
     * Prefetch a page and store in cache
     */
    async prefetchPage(url) {
        if (this.prefetchedUrls.has(url)) return;
        
        try {
            console.log(`🚀 Prefetching: ${url}`);
            const response = await fetch(url, {
                headers: {
                    'X-Prefetch': 'true'
                }
            });
            
            if (response.ok) {
                const html = await response.text();
                this.prefetchCache.set(url, {
                    html,
                    timestamp: Date.now()
                });
                this.prefetchedUrls.add(url);
                console.log(`✅ Prefetched: ${url}`);
            }
        } catch (error) {
            console.warn(`❌ Prefetch failed for ${url}:`, error);
        }
    }

    /**
     * Navigate using pushState with cached content
     */
    async navigateWithPushState(url) {
        const cached = this.prefetchCache.get(url);
        
        if (cached && this.isCacheValid(cached)) {
            // Use cached content
            this.loadCachedPage(url, cached.html);
        } else {
            // Fetch fresh content
            try {
                const response = await fetch(url);
                if (response.ok) {
                    const html = await response.text();
                    this.loadCachedPage(url, html);
                } else {
                    window.location.href = url; // Fallback to full page load
                }
            } catch (error) {
                console.error('Navigation failed:', error);
                window.location.href = url; // Fallback
            }
        }
    }

    /**
     * Load cached page content using pushState
     */
    loadCachedPage(url, html = null) {
        if (!html) {
            const cached = this.prefetchCache.get(url);
            if (!cached) return;
            html = cached.html;
        }

        // Parse the HTML response
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, 'text/html');
        
        // Update page title
        document.title = doc.title;
        
        // Update main content (adjust selector based on your app structure)
        const newContent = doc.querySelector('main') || doc.querySelector('.main-content') || doc.body;
        const currentContent = document.querySelector('main') || document.querySelector('.main-content');
        
        if (newContent && currentContent) {
            currentContent.innerHTML = newContent.innerHTML;
            
            // Re-initialize any JavaScript components
            this.reinitializeComponents();
            
            // Update URL
            history.pushState({ prefetched: true }, doc.title, url);
            
            // Scroll to top
            window.scrollTo(0, 0);
            
            console.log(`🎯 Navigated to: ${url}`);
        }
    }

    /**
     * Preload critical pages that users commonly visit
     */
    preloadCriticalPages() {
        const criticalPages = [
            '/login.html',
            '/register.html',
            '/profile.html',
            '/mobile.html'
        ];

        // Preload after a short delay to not block initial page load
        setTimeout(() => {
            criticalPages.forEach(page => {
                if (window.location.pathname !== page) {
                    this.prefetchPage(window.location.origin + page);
                }
            });
        }, 2000);
    }

    /**
     * Check if URL is internal
     */
    isInternalLink(url) {
        try {
            const urlObj = new URL(url, window.location.origin);
            return urlObj.origin === window.location.origin;
        } catch {
            return false;
        }
    }

    /**
     * Check if cached content is still valid (5 minutes)
     */
    isCacheValid(cached) {
        return Date.now() - cached.timestamp < 300000; // 5 minutes
    }

    /**
     * Reinitialize JavaScript components after content swap
     */
    reinitializeComponents() {
        // Trigger custom events for other scripts to reinitialize
        window.dispatchEvent(new CustomEvent('pageContentUpdated'));
        
        // Reinitialize any form handlers, event listeners, etc.
        if (window.initializePageScripts) {
            window.initializePageScripts();
        }
    }

    /**
     * Clear old cache entries to prevent memory bloat
     */
    cleanupCache() {
        const maxCacheSize = 50;
        const maxAge = 600000; // 10 minutes
        const now = Date.now();

        for (const [url, cached] of this.prefetchCache.entries()) {
            if (now - cached.timestamp > maxAge) {
                this.prefetchCache.delete(url);
                this.prefetchedUrls.delete(url);
            }
        }

        // If still too many entries, remove oldest
        if (this.prefetchCache.size > maxCacheSize) {
            const entries = Array.from(this.prefetchCache.entries())
                .sort((a, b) => a[1].timestamp - b[1].timestamp);
            
            const toRemove = entries.slice(0, entries.length - maxCacheSize);
            toRemove.forEach(([url]) => {
                this.prefetchCache.delete(url);
                this.prefetchedUrls.delete(url);
            });
        }
    }
}

// Initialize prefetch manager when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.prefetchManager = new PrefetchManager();
    });
} else {
    window.prefetchManager = new PrefetchManager();
}

// Cleanup cache periodically
setInterval(() => {
    if (window.prefetchManager) {
        window.prefetchManager.cleanupCache();
    }
}, 300000); // Every 5 minutes