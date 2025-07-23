/**
 * Asset Optimization System
 * Implements McMaster-Carr style asset loading and caching
 */

class AssetOptimizer {
    constructor() {
        this.imageCache = new Map();
        this.spriteSheets = new Map();
        this.lazyImages = [];
        this.observer = null;
        this.init();
    }

    init() {
        this.setupLazyLoading();
        this.optimizeImages();
        this.setupResourceHints();
        this.prefetchCriticalAssets();
    }

    /**
     * Setup lazy loading for images with Intersection Observer
     */
    setupLazyLoading() {
        // Create intersection observer for lazy loading
        this.observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    this.loadImage(entry.target);
                    this.observer.unobserve(entry.target);
                }
            });
        }, {
            rootMargin: '50px' // Start loading 50px before image comes into view
        });

        // Find all images with data-src (lazy loading)
        this.setupLazyImages();
    }

    /**
     * Setup lazy images and observe them
     */
    setupLazyImages() {
        const lazyImages = document.querySelectorAll('img[data-src]');
        lazyImages.forEach(img => {
            this.observer.observe(img);
        });

        // Add mutation observer to handle dynamically added images
        const mutationObserver = new MutationObserver((mutations) => {
            mutations.forEach(mutation => {
                mutation.addedNodes.forEach(node => {
                    if (node.nodeType === 1) { // Element node
                        const lazyImgs = node.querySelectorAll ? 
                            node.querySelectorAll('img[data-src]') : [];
                        lazyImgs.forEach(img => this.observer.observe(img));
                    }
                });
            });
        });

        mutationObserver.observe(document.body, {
            childList: true,
            subtree: true
        });
    }

    /**
     * Load image with optimizations
     */
    async loadImage(img) {
        const src = img.dataset.src;
        if (!src) return;

        try {
            // Create a new image to preload
            const newImg = new Image();
            
            // Set up loading placeholder
            img.classList.add('loading');
            
            newImg.onload = () => {
                img.src = src;
                img.classList.remove('loading');
                img.classList.add('loaded');
                
                // Remove data-src to prevent reprocessing
                delete img.dataset.src;
                
                // Cache the image
                this.imageCache.set(src, newImg);
                
                console.log(`🖼️ Image loaded: ${src}`);
            };
            
            newImg.onerror = () => {
                img.classList.remove('loading');
                img.classList.add('error');
                img.alt = 'Image failed to load';
                console.warn(`❌ Image failed: ${src}`);
            };
            
            // Start loading
            newImg.src = src;
            
        } catch (error) {
            console.error('Error loading image:', error);
            img.classList.remove('loading');
            img.classList.add('error');
        }
    }

    /**
     * Optimize all images on the page
     */
    optimizeImages() {
        const images = document.querySelectorAll('img');
        
        images.forEach(img => {
            // Add proper dimensions to prevent layout shift
            if (!img.width && !img.height && !img.style.width && !img.style.height) {
                img.style.aspectRatio = '1'; // Default aspect ratio
                img.style.width = '100%';
                img.style.height = 'auto';
            }
            
            // Add loading="lazy" for native lazy loading support
            if (!img.loading && !img.dataset.src) {
                img.loading = 'lazy';
            }
            
            // Add proper alt text if missing
            if (!img.alt) {
                img.alt = 'Image';
            }
        });
    }

    /**
     * Setup resource hints for better performance
     */
    setupResourceHints() {
        // DNS prefetch for external domains
        const externalDomains = [
            'cdn.jsdelivr.net',
            'fonts.googleapis.com',
            'fonts.gstatic.com'
        ];
        
        externalDomains.forEach(domain => {
            this.addResourceHint('dns-prefetch', `//${domain}`);
        });

        // Preconnect to critical external resources
        this.addResourceHint('preconnect', 'https://fonts.googleapis.com');
        this.addResourceHint('preconnect', 'https://fonts.gstatic.com', true);
    }

    /**
     * Add resource hint to document head
     */
    addResourceHint(rel, href, crossorigin = false) {
        const link = document.createElement('link');
        link.rel = rel;
        link.href = href;
        if (crossorigin) {
            link.crossOrigin = 'anonymous';
        }
        document.head.appendChild(link);
    }

    /**
     * Prefetch critical assets
     */
    prefetchCriticalAssets() {
        const criticalAssets = [
            '/api/leaderboard',
            '/api/videos',
            '/src/device-detection.js'
        ];

        // Prefetch after page load
        if (document.readyState === 'complete') {
            this.performPrefetch(criticalAssets);
        } else {
            window.addEventListener('load', () => {
                // Small delay to not interfere with critical loading
                setTimeout(() => this.performPrefetch(criticalAssets), 1000);
            });
        }
    }

    /**
     * Perform asset prefetching
     */
    performPrefetch(assets) {
        assets.forEach(asset => {
            if (asset.startsWith('/api/')) {
                // Prefetch API endpoints
                fetch(asset, { 
                    method: 'GET',
                    headers: { 'X-Prefetch': 'true' }
                }).then(response => {
                    if (response.ok) {
                        console.log(`🚀 API prefetched: ${asset}`);
                    }
                }).catch(err => {
                    console.warn(`❌ API prefetch failed: ${asset}`, err);
                });
            } else {
                // Prefetch static assets
                this.addResourceHint('prefetch', asset);
                console.log(`📦 Asset prefetched: ${asset}`);
            }
        });
    }

    /**
     * Create and manage sprite sheets for icons
     */
    createSpriteSheet(icons) {
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        
        // Calculate sprite sheet dimensions
        const iconSize = 24;
        const iconsPerRow = Math.ceil(Math.sqrt(icons.length));
        const spriteWidth = iconsPerRow * iconSize;
        const spriteHeight = Math.ceil(icons.length / iconsPerRow) * iconSize;
        
        canvas.width = spriteWidth;
        canvas.height = spriteHeight;
        
        // Generate sprite sheet
        let currentX = 0;
        let currentY = 0;
        const spriteMap = new Map();
        
        icons.forEach((iconData, index) => {
            // Draw icon to sprite sheet
            this.drawIconToSprite(ctx, iconData, currentX, currentY, iconSize);
            
            // Store sprite position
            spriteMap.set(iconData.name, {
                x: currentX,
                y: currentY,
                width: iconSize,
                height: iconSize
            });
            
            // Update position
            currentX += iconSize;
            if (currentX >= spriteWidth) {
                currentX = 0;
                currentY += iconSize;
            }
        });
        
        // Convert to data URL
        const spriteDataURL = canvas.toDataURL('image/png');
        this.spriteSheets.set('icons', { dataURL: spriteDataURL, map: spriteMap });
        
        console.log('🎨 Sprite sheet created with', icons.length, 'icons');
        return spriteDataURL;
    }

    /**
     * Draw icon to sprite sheet
     */
    drawIconToSprite(ctx, iconData, x, y, size) {
        // This is a simplified example - in practice you'd load actual icon images
        ctx.fillStyle = iconData.color || '#333';
        ctx.fillRect(x + 2, y + 2, size - 4, size - 4);
        
        // Add icon identifier
        ctx.fillStyle = '#fff';
        ctx.font = '10px Arial';
        ctx.fillText(iconData.name.charAt(0).toUpperCase(), x + size/2 - 3, y + size/2 + 3);
    }

    /**
     * Use sprite for displaying icons
     */
    useSpriteIcon(iconName, container) {
        const sprite = this.spriteSheets.get('icons');
        if (!sprite || !sprite.map.has(iconName)) {
            console.warn(`Icon not found in sprite: ${iconName}`);
            return;
        }
        
        const iconData = sprite.map.get(iconName);
        const iconElement = document.createElement('div');
        iconElement.className = 'sprite-icon';
        iconElement.style.cssText = `
            width: ${iconData.width}px;
            height: ${iconData.height}px;
            background-image: url(${sprite.dataURL});
            background-position: -${iconData.x}px -${iconData.y}px;
            background-repeat: no-repeat;
            display: inline-block;
        `;
        
        container.appendChild(iconElement);
    }

    /**
     * Optimize video loading
     */
    optimizeVideos() {
        const videos = document.querySelectorAll('video');
        
        videos.forEach(video => {
            // Add proper attributes for performance
            if (!video.hasAttribute('preload')) {
                video.preload = 'metadata'; // Load metadata only
            }
            
            // Add poster image if not present
            if (!video.poster && video.dataset.poster) {
                video.poster = video.dataset.poster;
            }
            
            // Setup lazy loading for videos
            if (video.dataset.src && !video.src) {
                this.observer.observe(video);
            }
        });
    }

    /**
     * Setup proper caching headers via meta tags
     */
    setupCacheHeaders() {
        const cacheHeaders = [
            { name: 'Cache-Control', content: 'public, max-age=31536000' }, // 1 year for static assets
            { name: 'Expires', content: new Date(Date.now() + 31536000000).toUTCString() }
        ];
        
        cacheHeaders.forEach(header => {
            const meta = document.createElement('meta');
            meta.httpEquiv = header.name;
            meta.content = header.content;
            document.head.appendChild(meta);
        });
    }

    /**
     * Monitor and report asset loading performance
     */
    monitorPerformance() {
        if ('PerformanceObserver' in window) {
            const observer = new PerformanceObserver((list) => {
                list.getEntries().forEach(entry => {
                    if (entry.entryType === 'resource') {
                        const loadTime = entry.responseEnd - entry.startTime;
                        console.log(`📊 ${entry.name}: ${loadTime.toFixed(2)}ms`);
                        
                        // Report slow assets
                        if (loadTime > 1000) {
                            console.warn(`🐌 Slow asset detected: ${entry.name} (${loadTime.toFixed(2)}ms)`);
                        }
                    }
                });
            });
            
            observer.observe({ entryTypes: ['resource'] });
        }
    }

    /**
     * Clean up resources
     */
    cleanup() {
        if (this.observer) {
            this.observer.disconnect();
        }
        this.imageCache.clear();
        this.spriteSheets.clear();
    }
}

// Initialize asset optimizer
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.assetOptimizer = new AssetOptimizer();
    });
} else {
    window.assetOptimizer = new AssetOptimizer();
}

// Clean up on page unload
window.addEventListener('beforeunload', () => {
    if (window.assetOptimizer) {
        window.assetOptimizer.cleanup();
    }
});

// Export for use in other scripts
window.AssetOptimizer = AssetOptimizer;