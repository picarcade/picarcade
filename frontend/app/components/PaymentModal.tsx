'use client';

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  X, CreditCard, Shield, Zap, CheckCircle, AlertCircle, 
  Loader2, ArrowLeft 
} from 'lucide-react';
import { loadStripe } from '@stripe/stripe-js';
import {
  Elements,
  CardElement,
  useStripe,
  useElements
} from '@stripe/react-stripe-js';

// Initialize Stripe
const stripePromise = loadStripe(process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY!);

interface Tier {
  id: string;
  tier_name: string;
  tier_level: number;
  tier_display_name: string;
  tier_description: string;
  monthly_price_usd: number;
  monthly_price_aud: number;
  monthly_xp_allocation: number;
}

interface PaymentModalProps {
  isOpen: boolean;
  onClose: () => void;
  selectedTier: Tier | null;
  currentTier?: number;
  currency?: 'usd' | 'aud';
  onSuccess: (subscriptionId: string) => void;
}

const cardElementOptions = {
  style: {
    base: {
      fontSize: '16px',
      color: '#424770',
      '::placeholder': {
        color: '#aab7c4',
      },
    },
    invalid: {
      color: '#9e2146',
    },
  },
};

interface PaymentFormProps {
  tier: Tier;
  currency: 'usd' | 'aud';
  onSuccess: (subscriptionId: string) => void;
  onBack: () => void;
}

function PaymentForm({ tier, currency, onSuccess, onBack }: PaymentFormProps) {
  const stripe = useStripe();
  const elements = useElements();
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [paymentStep, setPaymentStep] = useState<'form' | 'processing' | 'success' | 'error'>('form');
  const [cardReady, setCardReady] = useState(false);
  const [stripeReady, setStripeReady] = useState(false);

  // Monitor Stripe readiness
  React.useEffect(() => {
    if (stripe && elements) {
      setStripeReady(true);
      console.log('Stripe and Elements ready');
    }
  }, [stripe, elements]);

  // Cleanup function to reset state when component unmounts
  React.useEffect(() => {
    return () => {
      setPaymentStep('form');
      setIsProcessing(false);
      setError(null);
    };
  }, []);

  const price = currency === 'usd' ? tier.monthly_price_usd : tier.monthly_price_aud;
  const currencySymbol = currency === 'usd' ? '$' : 'A$';

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();

    if (!stripe || !elements) {
      console.error('Stripe not loaded:', { stripe: !!stripe, elements: !!elements });
      setError('Payment system not ready. Please wait a moment and try again.');
      return;
    }

    if (!stripeReady) {
      console.error('Stripe not fully initialized');
      setError('Payment system initializing. Please wait a moment and try again.');
      return;
    }

    if (!cardReady) {
      console.error('Card element not ready');
      setError('Card details not ready. Please wait a moment and try again.');
      return;
    }

    setIsProcessing(true);
    setError(null);

    // Get the card element BEFORE changing any state that might trigger re-renders
    const cardElement = elements.getElement(CardElement);
    
    if (!cardElement) {
      console.error('Card element not found. Elements state:', {
        elements: !!elements,
        stripe: !!stripe,
        cardReady
      });
      setError('Payment form not ready. Please close and reopen the payment modal.');
      setIsProcessing(false);
      return;
    }

    console.log('Card element successfully retrieved:', !!cardElement);

    try {
      console.log('Creating payment method...');
      
      // Create payment method
      const { error: paymentMethodError, paymentMethod } = await stripe.createPaymentMethod({
        type: 'card',
        card: cardElement,
      });

      if (paymentMethodError) {
        console.error('Payment method error:', paymentMethodError);
        throw new Error(paymentMethodError.message);
      }

      console.log('Payment method created successfully:', paymentMethod?.id);

      // Only change to processing state AFTER we have the payment method
      setPaymentStep('processing');

      // Call your backend to create subscription
      const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${baseUrl}/api/v1/subscriptions/create`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
        },
        body: JSON.stringify({
          tier_name: tier.tier_name,
          payment_method_id: paymentMethod.id,
          currency: currency,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Payment failed');
      }

      const result = await response.json();
      
      if (result.success) {
        setPaymentStep('success');
        setTimeout(() => {
          onSuccess(result.subscription_id);
        }, 2000);
      } else {
        throw new Error('Subscription creation failed');
      }
    } catch (err: unknown) {
      console.error('Payment process error:', err);
      
      let message = 'Payment failed';
      if (err instanceof Error) {
        message = err.message;
        
        // Specific handling for Stripe Element errors
        if (message.includes('Element') || message.includes('mounted') || message.includes('IntegrationError')) {
          message = 'Payment form error. Please close this modal and try again.';
          console.error('Stripe Element unmounting detected. Component state:', {
            paymentStep,
            isProcessing,
            cardReady,
            stripeReady,
            hasElements: !!elements,
            hasStripe: !!stripe
          });
        }
      }
      
      setError(message);
      setPaymentStep('error');
    } finally {
      setIsProcessing(false);
    }
  };

  if (paymentStep === 'processing') {
    return (
      <div className="relative">
        {/* Keep the form rendered but overlay with processing state */}
        <div className="opacity-30 pointer-events-none">
          <div className="flex items-center mb-6">
            <button
              onClick={onBack}
              className="p-2 hover:bg-gray-100 rounded-lg mr-3"
              disabled
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div>
              <h3 className="text-lg font-semibold">Complete Payment</h3>
              <p className="text-sm text-gray-600">
                {tier.tier_display_name} - {currencySymbol}{price}/month
              </p>
            </div>
          </div>

          <form className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Card Information
              </label>
              <div className="border rounded-lg p-4">
                <CardElement 
                  options={cardElementOptions}
                  onReady={() => setCardReady(true)}
                  onChange={(event) => {
                    if (event.error) {
                      setError(event.error.message);
                    } else {
                      setError(null);
                    }
                  }}
                />
              </div>
            </div>
          </form>
        </div>
        
        {/* Processing overlay */}
        <div className="absolute inset-0 flex items-center justify-center bg-white bg-opacity-95 rounded-lg">
          <div className="text-center py-8">
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
              className="inline-block"
            >
              <Loader2 className="w-12 h-12 text-blue-500" />
            </motion.div>
            <h3 className="text-lg font-semibold mt-4 mb-2">Processing Payment</h3>
            <p className="text-gray-600">Please wait while we set up your subscription...</p>
          </div>
        </div>
      </div>
    );
  }

  if (paymentStep === 'success') {
    return (
      <div className="text-center py-8">
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ type: "spring", duration: 0.5 }}
        >
          <CheckCircle className="w-12 h-12 text-green-500 mx-auto" />
        </motion.div>
        <h3 className="text-lg font-semibold mt-4 mb-2">Payment Successful!</h3>
        <p className="text-gray-600">Welcome to {tier.tier_display_name}!</p>
      </div>
    );
  }

  if (paymentStep === 'error') {
    return (
      <div className="text-center py-8">
        <AlertCircle className="w-12 h-12 text-red-500 mx-auto" />
        <h3 className="text-lg font-semibold mt-4 mb-2">Payment Failed</h3>
        <p className="text-red-600 mb-4">{error}</p>
        <button
          onClick={() => {
            setPaymentStep('form');
            setError(null);
          }}
          className="bg-blue-500 text-white px-4 py-2 rounded-lg hover:bg-blue-600 transition-colors"
        >
          Try Again
        </button>
      </div>
    );
  }

  return (
    <div>
      {/* Header */}
      <div className="flex items-center mb-6">
        <button
          onClick={onBack}
          className="p-2 hover:bg-gray-100 rounded-lg mr-3"
        >
          <ArrowLeft className="w-5 h-5" />
        </button>
        <div>
          <h3 className="text-lg font-semibold">Complete Payment</h3>
          <p className="text-sm text-gray-600">
            {tier.tier_display_name} - {currencySymbol}{price}/month
          </p>
        </div>
      </div>

      {/* Payment Form */}
      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Card Input */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Card Information
          </label>
          <div className="border rounded-lg p-4 focus-within:ring-2 focus-within:ring-blue-500 focus-within:border-blue-500">
            <CardElement 
              options={cardElementOptions}
              onReady={() => setCardReady(true)}
              onChange={(event) => {
                if (event.error) {
                  setError(event.error.message);
                } else {
                  setError(null);
                }
              }}
            />
          </div>
        </div>

        {/* Security Notice */}
        <div className="flex items-start space-x-3 p-4 bg-gray-50 rounded-lg">
          <Shield className="w-5 h-5 text-green-500 mt-0.5" />
          <div>
            <p className="text-sm font-medium text-gray-800">Secure Payment</p>
            <p className="text-xs text-gray-600">
              Your payment information is encrypted and secure. We use Stripe for processing.
            </p>
          </div>
        </div>

        {/* Billing Summary */}
        <div className="border rounded-lg p-4 bg-gray-50">
          <h4 className="font-medium mb-3">Billing Summary</h4>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span>{tier.tier_display_name}</span>
              <span>{currencySymbol}{price}/month</span>
            </div>
            <div className="flex justify-between">
              <span>XP Allocation</span>
              <span className="text-green-600">{tier.monthly_xp_allocation.toLocaleString()} XP</span>
            </div>
            <div className="border-t pt-2 font-medium">
              <div className="flex justify-between">
                <span>Total</span>
                <span>{currencySymbol}{price}/month</span>
              </div>
            </div>
          </div>
        </div>

        {error && (
          <div className="flex items-center space-x-2 p-3 bg-red-50 border border-red-200 rounded-lg">
            <AlertCircle className="w-4 h-4 text-red-500" />
            <span className="text-sm text-red-700">{error}</span>
          </div>
        )}

        {/* Submit Button */}
        <button
          type="submit"
          disabled={!stripe || !stripeReady || isProcessing || !cardReady}
          className="w-full bg-gradient-to-r from-blue-500 to-blue-600 text-white py-3 px-4 rounded-lg font-medium hover:from-blue-600 hover:to-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 flex items-center justify-center space-x-2"
        >
          {isProcessing ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>Processing...</span>
            </>
          ) : !stripeReady ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>Loading payment system...</span>
            </>
          ) : !cardReady ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>Card form loading...</span>
            </>
          ) : (
            <>
              <CreditCard className="w-4 h-4" />
              <span>Subscribe for {currencySymbol}{price}/month</span>
            </>
          )}
        </button>

        <p className="text-xs text-gray-500 text-center">
          By subscribing, you agree to our Terms of Service and Privacy Policy.
          You can cancel anytime.
        </p>
      </form>
    </div>
  );
}

function PaymentModalContent({
  selectedTier,
  currentTier,
  currency,
  onSuccess,
  onClose
}: {
  selectedTier: Tier;
  currentTier?: number;
  currency: 'usd' | 'aud';
  onSuccess: (subscriptionId: string) => void;
  onClose: () => void;
}) {
  const [showPaymentForm, setShowPaymentForm] = useState(false);

  const handleProceedToPayment = () => {
    setShowPaymentForm(true);
  };

  const handleBackToTier = () => {
    setShowPaymentForm(false);
  };

  const price = currency === 'usd' ? selectedTier.monthly_price_usd : selectedTier.monthly_price_aud;
  const currencySymbol = currency === 'usd' ? '$' : 'A$';
  const isUpgrade = currentTier && selectedTier.tier_level > currentTier;

  return (
    <>
      {/* Close Button */}
      <button
        onClick={onClose}
        className="absolute top-4 right-4 p-2 hover:bg-gray-100 rounded-lg transition-colors z-10"
      >
        <X className="w-5 h-5" />
      </button>

      {!showPaymentForm ? (
        /* Tier Confirmation */
        <div>
          <div className="text-center mb-6">
            <div className="inline-flex p-3 bg-gradient-to-r from-blue-500 to-blue-600 rounded-xl mb-4">
              <Zap className="w-6 h-6 text-white" />
            </div>
            <h3 className="text-xl font-bold text-gray-900 mb-2">
              {isUpgrade ? 'Upgrade to' : 'Subscribe to'} {selectedTier.tier_display_name}
            </h3>
            <p className="text-gray-600">
              {selectedTier.tier_description}
            </p>
          </div>

          {/* Features */}
          <div className="space-y-3 mb-6">
            <div className="flex items-center justify-between p-3 bg-green-50 rounded-lg">
              <div className="flex items-center space-x-2">
                <Zap className="w-4 h-4 text-green-600" />
                <span className="text-sm font-medium">Monthly XP Allocation</span>
              </div>
              <span className="text-green-700 font-bold">
                {selectedTier.monthly_xp_allocation.toLocaleString()} XP
              </span>
            </div>
          </div>

          {/* Pricing */}
          <div className="text-center mb-6 p-4 bg-gray-50 rounded-lg">
            <div className="text-3xl font-bold text-gray-900 mb-1">
              {currencySymbol}{price}
              <span className="text-lg font-normal text-gray-600">/month</span>
            </div>
            <p className="text-sm text-gray-600">
              Cancel anytime • No long-term commitment
            </p>
          </div>

          {/* Action Buttons */}
          <div className="space-y-3">
            <button
              onClick={handleProceedToPayment}
              className="w-full bg-gradient-to-r from-blue-500 to-blue-600 text-white py-3 px-4 rounded-lg font-medium hover:from-blue-600 hover:to-blue-700 transition-all duration-200 flex items-center justify-center space-x-2"
            >
              <CreditCard className="w-4 h-4" />
              <span>Continue to Payment</span>
            </button>
            
            <button
              onClick={onClose}
              className="w-full bg-gray-100 text-gray-700 py-3 px-4 rounded-lg font-medium hover:bg-gray-200 transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      ) : (
        /* Payment Form */
        <PaymentForm
          tier={selectedTier}
          currency={currency}
          onSuccess={onSuccess}
          onBack={handleBackToTier}
        />
      )}
    </>
  );
}

export default function PaymentModal({
  isOpen,
  onClose,
  selectedTier,
  currentTier,
  currency = 'usd',
  onSuccess
}: PaymentModalProps) {
  const handleClose = () => {
    onClose();
  };

  if (!selectedTier) return null;

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          <div className="flex items-center justify-center min-h-screen px-4 pt-4 pb-20 text-center sm:block sm:p-0">
            {/* Backdrop */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black bg-opacity-50 transition-opacity"
              onClick={handleClose}
            />

            {/* Modal */}
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 20 }}
              transition={{ duration: 0.2 }}
              className="inline-block w-full max-w-md p-6 my-8 overflow-hidden text-left align-middle transition-all transform bg-white shadow-xl rounded-2xl relative"
            >
              {/* Wrap everything in Elements to prevent remounting */}
              <Elements 
                stripe={stripePromise}
                key={`payment-${selectedTier.id}`} // Stable key to prevent unmounting
              >
                <PaymentModalContent
                  selectedTier={selectedTier}
                  currentTier={currentTier}
                  currency={currency}
                  onSuccess={onSuccess}
                  onClose={handleClose}
                />
              </Elements>
            </motion.div>
          </div>
        </div>
      )}
    </AnimatePresence>
  );
} 