'use client';

import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { ArrowLeft, Settings } from 'lucide-react';
import { useRouter } from 'next/navigation';
import dynamic from 'next/dynamic';
import SubscriptionTiers from '../components/SubscriptionTiers';

// Dynamically import PaymentModal to avoid SSR issues with Stripe
const PaymentModal = dynamic(() => import('../components/PaymentModal'), { 
  ssr: false,
  loading: () => <div>Loading payment form...</div>
});

interface Tier {
  id: string;
  tier_name: string;
  tier_level: number;
  tier_display_name: string;
  tier_description: string;
  monthly_price_usd: number;
  monthly_price_aud: number;
  monthly_xp_allocation: number;
  ai_models_included: string[];
  generation_types_allowed: string[];
  tier_icon: string;
  tier_color: string;
  priority_processing: boolean;
}

interface Subscription {
  tier_name: string;
  tier_level: number;
  tier_display_name: string;
  xp_balance: number;
  xp_allocated_this_period: number;
  xp_used_this_period: number;
  status: string;
  current_period_end?: string;

}

export default function SubscriptionsPage() {
  const router = useRouter();
  const [tiers, setTiers] = useState<Tier[]>([]);
  const [subscription, setSubscription] = useState<Subscription | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedTier, setSelectedTier] = useState<Tier | null>(null);
  const [showPaymentModal, setShowPaymentModal] = useState(false);

  useEffect(() => {
    loadSubscriptionData();
  }, []);

  const loadSubscriptionData = async () => {
    setIsLoading(true);
    try {
      const token = localStorage.getItem('access_token');
      const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const headers = {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      };

      // Load subscription tiers
      try {
        const tiersResponse = await fetch(`${baseUrl}/api/v1/subscriptions/tiers`, { headers });
        if (tiersResponse.ok) {
          const tiersData = await tiersResponse.json();
          setTiers(tiersData);
        }
      } catch (error) {
        console.error('Error loading tiers:', error);
      }

      // Load current subscription
      try {
        const subResponse = await fetch(`${baseUrl}/api/v1/subscriptions/current`, { headers });
        if (subResponse.ok) {
          const subData = await subResponse.json();
          setSubscription(subData);
        }
      } catch (error) {
        console.error('Error loading subscription:', error);
      }
    } catch (error) {
      console.error('Error loading subscription data:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleTierSelect = (tier: Tier) => {
    setSelectedTier(tier);
    setShowPaymentModal(true);
  };

  const handlePaymentSuccess = () => {
    setShowPaymentModal(false);
    setSelectedTier(null);
    // Reload subscription data
    loadSubscriptionData();
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 py-4 sm:py-8">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="flex items-start sm:items-center justify-between mb-6 sm:mb-8 flex-col sm:flex-row gap-4 sm:gap-0">
          <div className="flex items-center space-x-4">
            <button
              onClick={() => router.back()}
              className="p-2 hover:bg-gray-700/50 rounded-lg transition-colors"
            >
              <ArrowLeft className="w-5 h-5 text-white" />
            </button>
            <div>
              <h1 className="text-2xl sm:text-3xl font-bold text-white">
                Level Up
              </h1>
            </div>
          </div>

          <div className="flex items-center space-x-4 ml-auto sm:ml-0">
            <button 
              onClick={() => router.push('/subscriptions/manage')}
              className="p-2 hover:bg-gray-700/50 rounded-lg transition-colors"
              title="Manage Subscription"
            >
              <Settings className="w-5 h-5 text-white" />
            </button>
          </div>
        </div>

        {/* Content */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
        >
          <SubscriptionTiers
            tiers={tiers}
            currentTier={subscription?.tier_level}
            onSelectTier={handleTierSelect}
            isLoading={isLoading}
          />
        </motion.div>
      </div>

      {/* Payment Modal - Dynamically loaded */}
      {showPaymentModal && selectedTier && (
        <PaymentModal
          isOpen={showPaymentModal}
          onClose={() => {
            setShowPaymentModal(false);
            setSelectedTier(null);
          }}
          selectedTier={selectedTier}
          currentTier={subscription?.tier_level}
          currency="aud"
          onSuccess={handlePaymentSuccess}
        />
      )}
    </div>
  );
} 