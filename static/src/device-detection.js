// Enhanced Device Detection with Resolution-based Routing
// This script handles automatic routing between desktop and mobile versions

function getDeviceInfo() {
  const userAgent = navigator.userAgent.toLowerCase();
  const screenWidth = window.screen.width;
  const screenHeight = window.screen.height;
  const devicePixelRatio = window.devicePixelRatio || 1;
  const viewportWidth = window.innerWidth;
  const viewportHeight = window.innerHeight;
  
  // Calculate actual physical screen dimensions
  const physicalWidth = screenWidth * devicePixelRatio;
  const physicalHeight = screenHeight * devicePixelRatio;
  
  return {
    userAgent,
    screenWidth,
    screenHeight,
    devicePixelRatio,
    viewportWidth,
    viewportHeight,
    physicalWidth,
    physicalHeight,
    orientation: screenWidth > screenHeight ? 'landscape' : 'portrait'
  };
}

function isMobileDevice() {
  const device = getDeviceInfo();
  
  // User Agent detection for mobile devices
  const mobileUserAgents = /android|webos|iphone|ipad|ipod|blackberry|iemobile|opera mini|mobile|tablet/i;
  const isUserAgentMobile = mobileUserAgents.test(device.userAgent);
  
  // Resolution-based detection
  const maxMobileWidth = 768;  // Standard tablet breakpoint
  const maxMobileHeight = 1024; // Max mobile height in portrait
  
  // Consider device mobile if:
  // 1. User agent indicates mobile/tablet
  // 2. Screen width is less than 768px
  // 3. Viewport width is less than 768px (for responsive testing)
  // 4. Touch capability exists and screen is small
  const isResolutionMobile = device.screenWidth <= maxMobileWidth || 
                            device.viewportWidth <= maxMobileWidth;
  
  // Touch detection
  const isTouchDevice = 'ontouchstart' in window || 
                       navigator.maxTouchPoints > 0 || 
                       navigator.msMaxTouchPoints > 0;
  
  // Final determination
  const isMobile = isUserAgentMobile || 
                  isResolutionMobile || 
                  (isTouchDevice && device.screenWidth <= 1024);
  
  return {
    isMobile,
    isUserAgentMobile,
    isResolutionMobile,
    isTouchDevice,
    deviceInfo: device
  };
}

function getTargetPage(currentPath) {
  const detection = isMobileDevice();
  const currentFile = currentPath.split('/').pop() || 'index.html';
  
  // Skip redirect if user has forced a specific version
  if (localStorage.getItem('force-desktop') && !detection.isMobile) {
    return null; // Stay on current page
  }
  
  if (localStorage.getItem('force-mobile') && detection.isMobile) {
    return null; // Stay on current page
  }
  
  // Mobile mappings
  const mobilePages = {
    'index.html': 'mobile.html',
    '': 'mobile.html', // Root path
    'login.html': 'mobile-login.html',
    'register.html': 'mobile-register.html',
    'profile.html': 'mobile-profile.html',
    'forgot-password.html': 'mobile-forgot-password.html',
    'reset-password.html': 'mobile-reset-password.html'
  };
  
  // Desktop mappings (reverse)
  const desktopPages = {
    'mobile.html': 'index.html',
    'mobile-login.html': 'login.html',
    'mobile-register.html': 'register.html',
    'mobile-profile.html': 'profile.html',
    'mobile-forgot-password.html': 'forgot-password.html',
    'mobile-reset-password.html': 'reset-password.html'
  };
  
  if (detection.isMobile && mobilePages[currentFile]) {
    return mobilePages[currentFile];
  }
  
  if (!detection.isMobile && desktopPages[currentFile]) {
    return desktopPages[currentFile];
  }
  
  return null; // No redirect needed
}

function performDeviceRedirect() {
  const currentPath = window.location.pathname;
  const targetPage = getTargetPage(currentPath);
  
  if (targetPage) {
    // Preserve URL parameters and hash
    const search = window.location.search;
    const hash = window.location.hash;
    const newUrl = targetPage + search + hash;
    
    window.location.href = newUrl;
    return true; // Redirect performed
  }
  
  return false; // No redirect needed
}

// Functions to force specific version
function forceDesktopVersion() {
  localStorage.setItem('force-desktop', 'true');
  localStorage.removeItem('force-mobile');
  
  const currentFile = window.location.pathname.split('/').pop();
  const desktopPages = {
    'mobile.html': 'index.html',
    'mobile-login.html': 'login.html',
    'mobile-register.html': 'register.html',
    'mobile-profile.html': 'profile.html',
    'mobile-forgot-password.html': 'forgot-password.html',
    'mobile-reset-password.html': 'reset-password.html'
  };
  
  if (desktopPages[currentFile]) {
    const search = window.location.search;
    const hash = window.location.hash;
    window.location.href = desktopPages[currentFile] + search + hash;
  }
}

function forceMobileVersion() {
  localStorage.setItem('force-mobile', 'true');
  localStorage.removeItem('force-desktop');
  
  const currentFile = window.location.pathname.split('/').pop() || 'index.html';
  const mobilePages = {
    'index.html': 'mobile.html',
    'login.html': 'mobile-login.html',
    'register.html': 'mobile-register.html',
    'profile.html': 'mobile-profile.html',
    'forgot-password.html': 'mobile-forgot-password.html',
    'reset-password.html': 'mobile-reset-password.html'
  };
  
  if (mobilePages[currentFile]) {
    const search = window.location.search;
    const hash = window.location.hash;
    window.location.href = mobilePages[currentFile] + search + hash;
  }
}

function resetDevicePreference() {
  localStorage.removeItem('force-desktop');
  localStorage.removeItem('force-mobile');
  performDeviceRedirect();
}

// Debug function to log device information
function logDeviceInfo() {
  const detection = isMobileDevice();
  console.log('Device Detection Results:', {
    isMobile: detection.isMobile,
    isUserAgentMobile: detection.isUserAgentMobile,
    isResolutionMobile: detection.isResolutionMobile,
    isTouchDevice: detection.isTouchDevice,
    deviceInfo: detection.deviceInfo,
    forceDesktop: localStorage.getItem('force-desktop'),
    forceMobile: localStorage.getItem('force-mobile')
  });
}

// Auto-execute redirect on page load (unless script is included with data-no-redirect)
if (document.currentScript && !document.currentScript.hasAttribute('data-no-redirect')) {
  document.addEventListener('DOMContentLoaded', function() {
    // Small delay to ensure page is ready
    setTimeout(performDeviceRedirect, 100);
  });
}

// Export functions for global use
window.DeviceDetection = {
  isMobileDevice,
  getDeviceInfo,
  performDeviceRedirect,
  forceDesktopVersion,
  forceMobileVersion,
  resetDevicePreference,
  logDeviceInfo
};