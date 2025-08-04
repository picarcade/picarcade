# Stripe CLI Testing Guide

This guide helps you test your Stripe integration using the Stripe CLI to debug payment issues.

## Prerequisites

1. Install Stripe CLI:
   ```bash
   # Windows (using Scoop)
   scoop bucket add stripe https://github.com/stripe/scoop-stripe-cli.git
   scoop install stripe
   
   # Or download from: https://github.com/stripe/stripe-cli/releases
   ```

2. Authenticate with your Stripe account:
   ```bash
   stripe login
   ```

## Testing Payment Flow

### 1. Listen to Webhook Events

Start the webhook listener to see real-time events:

```bash
stripe listen --forward-to localhost:8000/api/v1/subscriptions/stripe-webhook
```

This will:
- Show you the webhook signing secret
- Forward events to your local backend
- Display all payment events in real-time

### 2. Trigger Test Events

In another terminal, trigger test payment events:

```bash
# Test successful payment
stripe trigger payment_intent.succeeded

# Test failed payment
stripe trigger payment_intent.payment_failed

# Test subscription created
stripe trigger customer.subscription.created

# Test subscription updated
stripe trigger customer.subscription.updated
```

### 3. Test Card Numbers

Use these test card numbers in your frontend:

```bash
# Successful payment
4242424242424242

# Card declined
4000000000000002

# Insufficient funds
4000000000009995

# Requires authentication (3D Secure)
4000002500003155

# Use any future expiry date and any 3-digit CVC
```

## Debugging Commands

### Check Payment Intents
```bash
# List recent payment intents
stripe payment_intents list --limit 5

# Get specific payment intent
stripe payment_intents retrieve pi_xxxxxxxxxxxxx
```

### Check Subscriptions
```bash
# List subscriptions
stripe subscriptions list --limit 5

# Get specific subscription
stripe subscriptions retrieve sub_xxxxxxxxxxxxx
```

### Check Customers
```bash
# List customers
stripe customers list --limit 5

# Get specific customer
stripe customers retrieve cus_xxxxxxxxxxxxx
```

## Common Issues and Solutions

### 1. Element Not Mounted Error
- **Symptoms**: "IntegrationError: We could not retrieve data from the specified Element"
- **Solution**: Check component mounting/unmounting in browser dev tools
- **Debug**: Run the debug script in browser console: `debugStripeElements()`

### 2. Webhook Signature Verification
- **Symptoms**: 400/401 errors on webhook endpoint
- **Solution**: Ensure webhook secret matches between Stripe CLI and backend
- **Debug**: Check webhook events in Stripe CLI output

### 3. Payment Method Creation Fails
- **Symptoms**: createPaymentMethod returns error
- **Solution**: Check card element state and validation
- **Debug**: Use test card numbers and check network tab

## Environment Variables Check

Verify your environment variables are correct:

```bash
# Frontend (.env.local)
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_...

# Backend 
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_... (from stripe listen command)
```

## Monitoring

1. **Stripe Dashboard**: Check https://dashboard.stripe.com/test/payments
2. **Browser Console**: Monitor for JavaScript errors
3. **Network Tab**: Check API request/response details
4. **Backend Logs**: Monitor your FastAPI server logs

## Quick Troubleshooting Checklist

- [ ] Stripe CLI authenticated and listening
- [ ] Correct publishable key in frontend
- [ ] Correct secret key in backend
- [ ] Webhook endpoint accessible
- [ ] CardElement properly mounted
- [ ] No JavaScript errors in console
- [ ] Valid test card number used
- [ ] Authentication token present