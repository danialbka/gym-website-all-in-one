/**
 * Critical CSS Inlining System
 * Implements McMaster-Carr style critical CSS loading
 */

class CriticalCSSManager {
    constructor() {
        this.criticalCSS = this.extractCriticalCSS();
        this.nonCriticalLoaded = false;
        this.init();
    }

    init() {
        this.inlineCriticalCSS();
        this.loadNonCriticalCSS();
        this.optimizeWebFonts();
    }

    /**
     * Extract critical CSS (above-the-fold styles)
     */
    extractCriticalCSS() {
        return `
            /* Critical CSS - Above the fold styles */
            
            /* Reset and base styles */
            * { box-sizing: border-box; }
            body { 
                margin: 0; 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                line-height: 1.5;
                color: #333;
                background: #fff;
            }
            
            /* Navigation - Always visible */
            nav, .navbar {
                display: flex;
                align-items: center;
                padding: 1rem;
                background: #1f2937;
                color: white;
                position: sticky;
                top: 0;
                z-index: 100;
            }
            
            nav a, .navbar a {
                color: white;
                text-decoration: none;
                padding: 0.5rem 1rem;
                border-radius: 0.25rem;
                transition: background-color 0.15s ease;
            }
            
            nav a:hover, .navbar a:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }
            
            /* Main content container - Critical for layout */
            main, .main-content {
                max-width: 1200px;
                margin: 0 auto;
                padding: 2rem 1rem;
            }
            
            /* Typography - Essential for readability */
            h1, h2, h3, h4, h5, h6 {
                margin: 0 0 1rem 0;
                font-weight: 600;
                line-height: 1.25;
            }
            
            h1 { font-size: 2.5rem; }
            h2 { font-size: 2rem; }
            h3 { font-size: 1.5rem; }
            
            /* Forms - Critical for user interaction */
            form {
                display: flex;
                flex-direction: column;
                gap: 1rem;
                max-width: 400px;
                margin: 0 auto;
            }
            
            input, select, textarea {
                padding: 0.75rem;
                border: 1px solid #d1d5db;
                border-radius: 0.375rem;
                font-size: 1rem;
            }
            
            input:focus, select:focus, textarea:focus {
                outline: 2px solid #3b82f6;
                outline-offset: 2px;
                border-color: #3b82f6;
            }
            
            button {
                padding: 0.75rem 1.5rem;
                background: #3b82f6;
                color: white;
                border: none;
                border-radius: 0.375rem;
                font-size: 1rem;
                cursor: pointer;
                transition: background-color 0.15s ease;
            }
            
            button:hover {
                background: #2563eb;
            }
            
            button:disabled {
                background: #9ca3af;
                cursor: not-allowed;
            }
            
            /* Loading states - Critical for UX */
            .loading {
                display: inline-block;
                width: 20px;
                height: 20px;
                border: 3px solid #f3f3f3;
                border-top: 3px solid #3498db;
                border-radius: 50%;
                animation: spin 1s linear infinite;
            }
            
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            
            /* Error and success messages */
            .error {
                color: #dc2626;
                background: #fef2f2;
                border: 1px solid #fecaca;
                padding: 1rem;
                border-radius: 0.375rem;
                margin: 1rem 0;
            }
            
            .success {
                color: #059669;
                background: #f0fdf4;
                border: 1px solid #bbf7d0;
                padding: 1rem;
                border-radius: 0.375rem;
                margin: 1rem 0;
            }
            
            /* Mobile responsiveness - Critical for mobile users */
            @media (max-width: 768px) {
                main, .main-content {
                    padding: 1rem 0.5rem;
                }
                
                h1 { font-size: 2rem; }
                h2 { font-size: 1.5rem; }
                
                nav, .navbar {
                    padding: 0.5rem;
                    flex-wrap: wrap;
                }
                
                form {
                    max-width: 100%;
                }
            }
            
            /* Hide non-critical content initially */
            .non-critical {
                visibility: hidden;
            }
            
            .non-critical.loaded {
                visibility: visible;
            }
        `;
    }

    /**
     * Inline critical CSS in the document head
     */
    inlineCriticalCSS() {
        // Remove existing critical CSS if present
        const existingCritical = document.querySelector('#critical-css');
        if (existingCritical) {
            existingCritical.remove();
        }

        // Create and inject critical CSS
        const style = document.createElement('style');
        style.id = 'critical-css';
        style.textContent = this.criticalCSS;
        
        // Insert before any other stylesheets
        const firstLink = document.querySelector('link[rel="stylesheet"]');
        if (firstLink) {
            document.head.insertBefore(style, firstLink);
        } else {
            document.head.appendChild(style);
        }

        console.log('✅ Critical CSS inlined');
    }

    /**
     * Load non-critical CSS asynchronously
     */
    loadNonCriticalCSS() {
        // Find all non-critical stylesheets
        const stylesheets = document.querySelectorAll('link[rel="stylesheet"][data-critical="false"]');
        
        if (stylesheets.length === 0) {
            // If no stylesheets marked as non-critical, load main CSS async
            this.loadStylesheetAsync('/src/output.css');
        } else {
            stylesheets.forEach(stylesheet => {
                this.loadStylesheetAsync(stylesheet.href);
                stylesheet.remove(); // Remove the blocking link
            });
        }

        // Load after initial render
        requestIdleCallback(() => {
            this.markNonCriticalContentVisible();
        });
    }

    /**
     * Load stylesheet asynchronously
     */
    loadStylesheetAsync(href) {
        const link = document.createElement('link');
        link.rel = 'stylesheet';
        link.href = href;
        link.media = 'print'; // Load as print to avoid render blocking
        link.onload = () => {
            link.media = 'all'; // Switch to all media once loaded
            this.nonCriticalLoaded = true;
            console.log(`📄 Non-critical CSS loaded: ${href}`);
        };
        
        document.head.appendChild(link);
    }

    /**
     * Make non-critical content visible after CSS loads
     */
    markNonCriticalContentVisible() {
        const nonCriticalElements = document.querySelectorAll('.non-critical');
        nonCriticalElements.forEach(element => {
            element.classList.add('loaded');
        });
    }

    /**
     * Optimize web font loading
     */
    optimizeWebFonts() {
        // Preload critical fonts
        const criticalFonts = [
            '/fonts/inter-regular.woff2',
            '/fonts/inter-medium.woff2'
        ];

        criticalFonts.forEach(fontUrl => {
            if (this.fontExists(fontUrl)) {
                const link = document.createElement('link');
                link.rel = 'preload';
                link.as = 'font';
                link.type = 'font/woff2';
                link.crossOrigin = 'anonymous';
                link.href = fontUrl;
                document.head.appendChild(link);
            }
        });

        // Add font-display: swap to existing font-face rules
        this.addFontDisplaySwap();
    }

    /**
     * Check if font file exists
     */
    fontExists(url) {
        // Simple check - in production you might want to verify file exists
        return true; // Assume fonts exist for now
    }

    /**
     * Add font-display: swap to improve font loading performance
     */
    addFontDisplaySwap() {
        const fontFaceCSS = `
            @font-face {
                font-family: 'Inter';
                font-style: normal;
                font-weight: 400;
                font-display: swap;
                src: local('Inter Regular'), local('Inter-Regular'),
                     url('/fonts/inter-regular.woff2') format('woff2');
            }
            
            @font-face {
                font-family: 'Inter';
                font-style: normal;
                font-weight: 500;
                font-display: swap;
                src: local('Inter Medium'), local('Inter-Medium'),
                     url('/fonts/inter-medium.woff2') format('woff2');
            }
        `;

        const style = document.createElement('style');
        style.textContent = fontFaceCSS;
        document.head.appendChild(style);
    }

    /**
     * Preload critical resources
     */
    preloadCriticalResources() {
        const criticalResources = [
            { href: '/src/prefetch.js', as: 'script' },
            { href: '/api/user/' + this.getCurrentUser(), as: 'fetch' }
        ];

        criticalResources.forEach(resource => {
            const link = document.createElement('link');
            link.rel = 'preload';
            link.href = resource.href;
            link.as = resource.as;
            if (resource.as === 'fetch') {
                link.crossOrigin = 'anonymous';
            }
            document.head.appendChild(link);
        });
    }

    /**
     * Get current user for preloading user-specific data
     */
    getCurrentUser() {
        // Try to get username from localStorage or other source
        return localStorage.getItem('username') || 'guest';
    }

    /**
     * Generate critical CSS for specific page types
     */
    static generatePageSpecificCSS(pageType) {
        const pageSpecificStyles = {
            'login': `
                .login-form { max-width: 400px; margin: 2rem auto; }
                .login-header { text-align: center; margin-bottom: 2rem; }
            `,
            'leaderboard': `
                .leaderboard-table { width: 100%; border-collapse: collapse; }
                .leaderboard-table th,
                .leaderboard-table td { padding: 0.75rem; text-align: left; border-bottom: 1px solid #e5e7eb; }
                .leaderboard-table th { background: #f9fafb; font-weight: 600; }
            `,
            'profile': `
                .profile-header { display: flex; align-items: center; gap: 1rem; margin-bottom: 2rem; }
                .profile-stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; }
                .stat-card { padding: 1.5rem; background: #f9fafb; border-radius: 0.5rem; }
            `
        };

        return pageSpecificStyles[pageType] || '';
    }
}

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.criticalCSSManager = new CriticalCSSManager();
    });
} else {
    window.criticalCSSManager = new CriticalCSSManager();
}

// Export for use in other scripts
window.CriticalCSSManager = CriticalCSSManager;