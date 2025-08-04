// Debug script for Stripe integration issues
// Run this in the browser console to diagnose Element mounting issues

function debugStripeElements() {
  console.log('=== Stripe Elements Debug Information ===');
  
  // Check if Stripe is loaded
  console.log('1. Stripe Library Status:');
  console.log('   - window.Stripe:', typeof window.Stripe);
  console.log('   - Stripe available:', !!window.Stripe);
  
  // Check for Elements on the page
  console.log('\n2. Elements on Page:');
  const stripeElements = document.querySelectorAll('.StripeElement, [class*="stripe"], [class*="Element"]');
  console.log('   - Found elements:', stripeElements.length);
  stripeElements.forEach((el, index) => {
    console.log(`   - Element ${index}:`, {
      className: el.className,
      isConnected: el.isConnected,
      parentNode: !!el.parentNode,
      offsetParent: !!el.offsetParent,
      style: el.style.display
    });
  });
  
  // Check React dev tools for component state
  console.log('\n3. Component Mount State:');
  try {
    const reactRoot = document.querySelector('#__next, [data-reactroot]');
    console.log('   - React root found:', !!reactRoot);
    
    // Look for payment modal in DOM
    const paymentModal = document.querySelector('[class*="modal"], [class*="payment"]');
    console.log('   - Payment modal found:', !!paymentModal);
    
    // Check for animation states
    const animatedElements = document.querySelectorAll('[style*="transform"], [style*="transition"]');
    console.log('   - Animated elements:', animatedElements.length);
  } catch (e) {
    console.log('   - Error checking React state:', e.message);
  }
  
  // Check localStorage for tokens
  console.log('\n4. Authentication:');
  console.log('   - Access token present:', !!localStorage.getItem('access_token'));
  
  // Environment check
  console.log('\n5. Environment:');
  console.log('   - URL:', window.location.href);
  console.log('   - User agent:', navigator.userAgent);
  
  console.log('\n=== Debug Complete ===');
  
  return {
    stripeLoaded: !!window.Stripe,
    elementsFound: stripeElements.length,
    hasToken: !!localStorage.getItem('access_token')
  };
}

// Auto-run if in browser console
if (typeof window !== 'undefined') {
  console.log('Stripe Debug Tool loaded. Run debugStripeElements() to diagnose issues.');
}

// For Node.js testing (if needed)
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { debugStripeElements };
}