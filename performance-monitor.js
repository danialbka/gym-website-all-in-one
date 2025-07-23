/**
 * Performance Monitoring System
 * McMaster-Carr style performance tracking and optimization
 */

class PerformanceMonitor {
    constructor() {
        this.metrics = {
            navigation: {},
            resources: [],
            userInteractions: [],
            apiCalls: []
        };
        this.thresholds = {
            fcp: 1800, // First Contentful Paint
            lcp: 2500, // Largest Contentful Paint
            fid: 100,  // First Input Delay
            cls: 0.1   // Cumulative Layout Shift
        };
        this.init();
    }

    init() {
        this.measureNavigationTiming();
        this.measureResourceTiming();
        this.measureWebVitals();
        this.monitorUserInteractions();
        this.startReporting();
    }

    /**
     * Measure navigation timing metrics
     */
    measureNavigationTiming() {
        if (!('performance' in window) || !window.performance.navigation) return;

        const nav = window.performance.navigation;
        const timing = window.performance.timing;

        this.metrics.navigation = {
            type: nav.type === 0 ? 'navigate' : nav.type === 1 ? 'reload' : 'back_forward',
            redirectCount: nav.redirectCount,
            dns: timing.domainLookupEnd - timing.domainLookupStart,
            tcp: timing.connectEnd - timing.connectStart,
            ssl: timing.secureConnectionStart > 0 ? timing.connectEnd - timing.secureConnectionStart : 0,
            ttfb: timing.responseStart - timing.navigationStart,
            domLoading: timing.domLoading - timing.navigationStart,
            domInteractive: timing.domInteractive - timing.navigationStart,
            domComplete: timing.domComplete - timing.navigationStart,
            loadComplete: timing.loadEventEnd - timing.navigationStart
        };

        console.log('📊 Navigation Metrics:', this.metrics.navigation);
        this.reportMetric('navigation', this.metrics.navigation);
    }

    /**
     * Measure resource loading performance
     */
    measureResourceTiming() {
        if (!('performance' in window) || !window.performance.getEntriesByType) return;

        const observer = new PerformanceObserver((list) => {
            list.getEntries().forEach(entry => {
                if (entry.entryType === 'resource') {
                    const resourceData = {
                        name: entry.name,
                        type: this.getResourceType(entry.name),
                        size: entry.transferSize || 0,
                        duration: entry.duration,
                        startTime: entry.startTime,
                        dns: entry.domainLookupEnd - entry.domainLookupStart,
                        tcp: entry.connectEnd - entry.connectStart,
                        ssl: entry.secureConnectionStart > 0 ? entry.connectEnd - entry.secureConnectionStart : 0,
                        ttfb: entry.responseStart - entry.requestStart,
                        download: entry.responseEnd - entry.responseStart
                    };

                    this.metrics.resources.push(resourceData);
                    
                    // Log slow resources
                    if (resourceData.duration > 1000) {
                        console.warn(`🐌 Slow resource: ${resourceData.name} (${resourceData.duration.toFixed(2)}ms)`);
                    }

                    this.reportMetric('resource', resourceData);
                }
            });
        });

        observer.observe({ entryTypes: ['resource'] });
    }

    /**
     * Measure Core Web Vitals
     */
    measureWebVitals() {
        // First Contentful Paint
        this.measureFCP();
        
        // Largest Contentful Paint
        this.measureLCP();
        
        // First Input Delay
        this.measureFID();
        
        // Cumulative Layout Shift
        this.measureCLS();
    }

    measureFCP() {
        if (!('PerformanceObserver' in window)) return;

        const observer = new PerformanceObserver((list) => {
            list.getEntries().forEach(entry => {
                if (entry.name === 'first-contentful-paint') {
                    const fcp = entry.startTime;
                    const status = fcp <= this.thresholds.fcp ? 'good' : fcp <= this.thresholds.fcp * 1.5 ? 'needs-improvement' : 'poor';
                    
                    console.log(`🎨 First Contentful Paint: ${fcp.toFixed(2)}ms (${status})`);
                    this.reportMetric('fcp', { value: fcp, status });
                }
            });
        });

        observer.observe({ entryTypes: ['paint'] });
    }

    measureLCP() {
        if (!('PerformanceObserver' in window)) return;

        const observer = new PerformanceObserver((list) => {
            const entries = list.getEntries();
            const lastEntry = entries[entries.length - 1];
            
            if (lastEntry) {
                const lcp = lastEntry.startTime;
                const status = lcp <= this.thresholds.lcp ? 'good' : lcp <= this.thresholds.lcp * 1.5 ? 'needs-improvement' : 'poor';
                
                console.log(`🖼️ Largest Contentful Paint: ${lcp.toFixed(2)}ms (${status})`);
                this.reportMetric('lcp', { value: lcp, status, element: lastEntry.element });
            }
        });

        observer.observe({ entryTypes: ['largest-contentful-paint'] });
    }

    measureFID() {
        if (!('PerformanceObserver' in window)) return;

        const observer = new PerformanceObserver((list) => {
            list.getEntries().forEach(entry => {
                const fid = entry.processingStart - entry.startTime;
                const status = fid <= this.thresholds.fid ? 'good' : fid <= this.thresholds.fid * 3 ? 'needs-improvement' : 'poor';
                
                console.log(`👆 First Input Delay: ${fid.toFixed(2)}ms (${status})`);
                this.reportMetric('fid', { value: fid, status });
            });
        });

        observer.observe({ entryTypes: ['first-input'] });
    }

    measureCLS() {
        if (!('PerformanceObserver' in window)) return;

        let clsValue = 0;
        let sessionValue = 0;
        let sessionEntries = [];

        const observer = new PerformanceObserver((list) => {
            list.getEntries().forEach(entry => {
                if (!entry.hadRecentInput) {
                    const firstSessionEntry = sessionEntries[0];
                    const lastSessionEntry = sessionEntries[sessionEntries.length - 1];

                    if (sessionValue && entry.startTime - lastSessionEntry.startTime < 1000 && 
                        entry.startTime - firstSessionEntry.startTime < 5000) {
                        sessionValue += entry.value;
                        sessionEntries.push(entry);
                    } else {
                        sessionValue = entry.value;
                        sessionEntries = [entry];
                    }

                    if (sessionValue > clsValue) {
                        clsValue = sessionValue;
                        const status = clsValue <= this.thresholds.cls ? 'good' : clsValue <= this.thresholds.cls * 2.5 ? 'needs-improvement' : 'poor';
                        
                        console.log(`📐 Cumulative Layout Shift: ${clsValue.toFixed(4)} (${status})`);
                        this.reportMetric('cls', { value: clsValue, status });
                    }
                }
            });
        });

        observer.observe({ entryTypes: ['layout-shift'] });
    }

    /**
     * Monitor user interactions for performance insights
     */
    monitorUserInteractions() {
        const interactions = ['click', 'keydown', 'scroll'];
        
        interactions.forEach(eventType => {
            document.addEventListener(eventType, (e) => {
                const timestamp = performance.now();
                
                this.metrics.userInteractions.push({
                    type: eventType,
                    timestamp,
                    target: e.target.tagName.toLowerCase(),
                    id: e.target.id || null,
                    className: e.target.className || null
                });
                
                // Keep only recent interactions (last 100)
                if (this.metrics.userInteractions.length > 100) {
                    this.metrics.userInteractions = this.metrics.userInteractions.slice(-100);
                }
            }, { passive: true });
        });
    }

    /**
     * Monitor API call performance
     */
    monitorApiCalls() {
        const originalFetch = window.fetch;
        
        window.fetch = async (...args) => {
            const startTime = performance.now();
            const url = args[0];
            
            try {
                const response = await originalFetch(...args);
                const endTime = performance.now();
                const duration = endTime - startTime;
                
                const apiData = {
                    url,
                    method: args[1]?.method || 'GET',
                    status: response.status,
                    duration,
                    timestamp: startTime,
                    success: response.ok
                };
                
                this.metrics.apiCalls.push(apiData);
                
                // Log slow API calls
                if (duration > 2000) {
                    console.warn(`🐌 Slow API call: ${url} (${duration.toFixed(2)}ms)`);
                }
                
                this.reportMetric('api', apiData);
                
                return response;
            } catch (error) {
                const endTime = performance.now();
                const duration = endTime - startTime;
                
                const apiData = {
                    url,
                    method: args[1]?.method || 'GET',
                    status: 0,
                    duration,
                    timestamp: startTime,
                    success: false,
                    error: error.message
                };
                
                this.metrics.apiCalls.push(apiData);
                this.reportMetric('api', apiData);
                
                throw error;
            }
        };
    }

    /**
     * Get resource type from URL
     */
    getResourceType(url) {
        if (url.includes('/api/')) return 'api';
        if (/\.(css)$/i.test(url)) return 'css';
        if (/\.(js)$/i.test(url)) return 'js';
        if (/\.(png|jpg|jpeg|gif|svg|webp|ico)$/i.test(url)) return 'image';
        if (/\.(woff|woff2|ttf|otf)$/i.test(url)) return 'font';
        if (/\.(mp4|webm|ogg)$/i.test(url)) return 'video';
        return 'other';
    }

    /**
     * Report metric to console and optionally to analytics
     */
    reportMetric(type, data) {
        // In production, send to analytics service
        if (typeof gtag !== 'undefined') {
            gtag('event', 'performance', {
                metric_type: type,
                metric_data: JSON.stringify(data)
            });
        }
        
        // Store in localStorage for debugging
        try {
            const perfData = JSON.parse(localStorage.getItem('gym-perf-data') || '[]');
            perfData.push({ type, data, timestamp: Date.now() });
            
            // Keep only last 50 metrics
            if (perfData.length > 50) {
                perfData.splice(0, perfData.length - 50);
            }
            
            localStorage.setItem('gym-perf-data', JSON.stringify(perfData));
        } catch (e) {
            // Ignore storage errors
        }
    }

    /**
     * Start periodic reporting
     */
    startReporting() {
        // Report summary every 30 seconds
        setInterval(() => {
            this.generatePerformanceReport();
        }, 30000);
        
        // Report on page unload
        window.addEventListener('beforeunload', () => {
            this.generatePerformanceReport();
        });
    }

    /**
     * Generate performance report
     */
    generatePerformanceReport() {
        const report = {
            timestamp: Date.now(),
            navigation: this.metrics.navigation,
            resources: {
                total: this.metrics.resources.length,
                totalSize: this.metrics.resources.reduce((sum, r) => sum + r.size, 0),
                avgDuration: this.metrics.resources.reduce((sum, r) => sum + r.duration, 0) / this.metrics.resources.length || 0,
                slowResources: this.metrics.resources.filter(r => r.duration > 1000).length
            },
            api: {
                total: this.metrics.apiCalls.length,
                avgDuration: this.metrics.apiCalls.reduce((sum, a) => sum + a.duration, 0) / this.metrics.apiCalls.length || 0,
                successRate: this.metrics.apiCalls.filter(a => a.success).length / this.metrics.apiCalls.length || 0,
                slowCalls: this.metrics.apiCalls.filter(a => a.duration > 2000).length
            },
            interactions: this.metrics.userInteractions.length
        };
        
        console.log('📈 Performance Report:', report);
        this.reportMetric('summary', report);
    }

    /**
     * Get current performance data
     */
    getMetrics() {
        return this.metrics;
    }

    /**
     * Clear metrics
     */
    clearMetrics() {
        this.metrics = {
            navigation: {},
            resources: [],
            userInteractions: [],
            apiCalls: []
        };
        localStorage.removeItem('gym-perf-data');
    }
}

// Initialize performance monitor
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.performanceMonitor = new PerformanceMonitor();
    });
} else {
    window.performanceMonitor = new PerformanceMonitor();
}

// Export for debugging
window.PerformanceMonitor = PerformanceMonitor;