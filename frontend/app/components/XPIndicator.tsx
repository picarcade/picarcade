'use client';

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Zap, Crown, Star, Gamepad2, AlertTriangle, Plus } from 'lucide-react';
import { useRouter } from 'next/navigation';

interface Subscription {
  tier_level: number;
  tier_display_name: string;
  xp_balance: number;
  status: string;
}

interface XPIndicatorProps {
  currentXP: number;
  generationCost?: number;
  generationType?: string;
  isGenerating?: boolean;
  onInsufficientXP?: () => void;
  className?: string;
}

const tierConfig = {
  1: { icon: Gamepad2, color: 'text-green-400', emoji: '🎮' },
  2: { icon: Star, color: 'text-blue-400', emoji: '🏆' },
  3: { icon: Crown, color: 'text-purple-400', emoji: '👑' }
};

export default function XPIndicator({
  currentXP,
  generationCost = 0,
  generationType = 'generation',
  isGenerating = false,
  onInsufficientXP,
  className = ''
}: XPIndicatorProps) {
  const router = useRouter();
  const [subscription, setSubscription] = useState<Subscription | null>(null);
  const [showWarning, setShowWarning] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    loadSubscriptionData();
  }, []);

  useEffect(() => {
    // Show warning if XP is insufficient
    if (generationCost > 0 && currentXP < generationCost) {
      setShowWarning(true);
      if (onInsufficientXP) {
        onInsufficientXP();
      }
    } else {
      setShowWarning(false);
    }
  }, [currentXP, generationCost, onInsufficientXP]);

  const loadSubscriptionData = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const headers = {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      };

      const response = await fetch(`${baseUrl}/api/v1/subscriptions/current`, { headers });
      if (response.ok) {
        const data = await response.json();
        setSubscription(data);
      }
    } catch (error) {
      console.error('Error loading subscription:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const currentTier = subscription ? tierConfig[subscription.tier_level as keyof typeof tierConfig] : tierConfig[1];
  const TierIcon = currentTier.icon;
  const hasInsufficientXP = generationCost > 0 && currentXP < generationCost;

  const getXPStatusColor = () => {
    if (hasInsufficientXP) return 'text-red-400';
    if (currentXP < 50) return 'text-yellow-400';
    return 'text-green-400';
  };

  if (isLoading) {
    return (
      <div className={`flex items-center space-x-2 ${className}`}>
        <div className="animate-pulse bg-gray-700 rounded-full h-8 w-24"></div>
      </div>
    );
  }

  return (
    <div className={`flex items-center space-x-2 ${className}`}>
      {/* XP Balance */}
      <motion.div
        className={`flex items-center space-x-2 px-3 py-1.5 rounded-full bg-gray-800/60 backdrop-blur-sm border border-gray-700/50 ${
          hasInsufficientXP ? 'border-red-500/50 bg-red-900/20' : ''
        }`}
        animate={isGenerating ? { scale: [1, 1.05, 1] } : {}}
        transition={{ duration: 2, repeat: Infinity }}
      >
        <TierIcon className={`w-4 h-4 ${currentTier.color}`} />
        
        <div className="flex items-center space-x-1">
          <Zap className={`w-4 h-4 ${getXPStatusColor()}`} />
          <span className={`text-sm font-medium ${getXPStatusColor()}`}>
            {currentXP.toLocaleString()}
          </span>
        </div>

        {generationCost > 0 && (
          <>
            <span className="text-gray-400 text-sm">-</span>
            <span className={`text-sm font-medium ${hasInsufficientXP ? 'text-red-400' : 'text-gray-300'}`}>
              {generationCost}
            </span>
          </>
        )}
      </motion.div>

      {/* Warning for insufficient XP */}
      <AnimatePresence>
        {showWarning && (
          <motion.div
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.8 }}
            className="flex items-center space-x-2"
          >
            <div className="p-1.5 bg-red-500/20 rounded-full">
              <AlertTriangle className="w-3 h-3 text-red-400" />
            </div>
            <button
              onClick={() => router.push('/subscriptions')}
              className="text-xs text-blue-400 hover:text-blue-300 underline"
            >
              Get More XP
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Low XP warning for balance under 50 */}
      {currentXP < 50 && currentXP > 0 && !hasInsufficientXP && (
        <motion.button
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          onClick={() => router.push('/subscriptions')}
          className="flex items-center space-x-1 px-2 py-1 bg-yellow-500/20 rounded-full text-yellow-400 hover:bg-yellow-500/30 transition-colors"
        >
          <Plus className="w-3 h-3" />
          <span className="text-xs">Top Up</span>
        </motion.button>
      )}

      {/* Generation type indicator */}
      {generationType && generationCost > 0 && (
        <div className="text-xs text-gray-500 hidden sm:block">
          {generationType.replace('_', ' ').toLowerCase()}
        </div>
      )}
    </div>
  );
} 