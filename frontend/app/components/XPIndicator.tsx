'use client';

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { AlertTriangle, Plus } from 'lucide-react';
import { useRouter } from 'next/navigation';

interface Subscription {
  tier_level: number;
  tier_display_name: string;
  xp_balance: number;
  xp_allocated_this_period: number;
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
  const [animatedXP, setAnimatedXP] = useState(currentXP);

  useEffect(() => {
    loadSubscriptionData();
  }, []);

  useEffect(() => {
    // Animate XP changes
    if (animatedXP !== currentXP) {
      setAnimatedXP(currentXP);
    }
  }, [currentXP, animatedXP]);

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

  const hasInsufficientXP = generationCost > 0 && currentXP < generationCost;
  
  // Calculate health bar percentage
  const maxXP = subscription?.xp_allocated_this_period || 1000; // fallback to 1000 if no subscription
  const healthPercentage = Math.max(0, Math.min(100, (currentXP / maxXP) * 100));
  const afterCostPercentage = generationCost > 0 
    ? Math.max(0, Math.min(100, ((currentXP - generationCost) / maxXP) * 100))
    : healthPercentage;

  // Determine health bar colors based on percentage
  const getHealthBarColor = (percentage: number) => {
    if (percentage > 60) return 'from-green-500 to-green-400';
    if (percentage > 30) return 'from-orange-500 to-orange-400';
    return 'from-red-500 to-red-400';
  };

  const getHealthBarBgColor = (percentage: number) => {
    if (percentage > 60) return 'bg-green-500/20';
    if (percentage > 30) return 'bg-orange-500/20';
    return 'bg-red-500/20';
  };

  const getXPStatusColor = () => {
    if (hasInsufficientXP) return 'text-red-400';
    if (healthPercentage <= 30) return 'text-red-400';
    if (healthPercentage <= 60) return 'text-orange-400';
    return 'text-green-400';
  };

  if (isLoading) {
    return (
      <div className={`flex items-center space-x-2 ${className}`}>
        <div className="animate-pulse bg-gray-700 rounded-full h-8 w-48"></div>
      </div>
    );
  }

  return (
    <div className={`flex items-center space-x-3 ${className}`}>
      {/* Health Bar Container */}
      <motion.div
        className={`flex items-center space-x-3 px-4 py-2 rounded-xl bg-gray-800/60 backdrop-blur-sm border border-gray-700/50 ${
          hasInsufficientXP ? 'border-red-500/50 bg-red-900/20' : ''
        }`}
        animate={isGenerating ? { scale: [1, 1.02, 1] } : {}}
        transition={{ duration: 2, repeat: Infinity }}
      >
        {/* Health Bar */}
        <div className="flex items-center space-x-2 min-w-0">
          <div className="flex flex-col space-y-1 min-w-0">
            {/* Health Bar Visual */}
            <div className="relative w-32 h-3 bg-gray-700 rounded-full overflow-hidden">
              {/* Background glow */}
              <div 
                className={`absolute inset-0 rounded-full ${getHealthBarBgColor(healthPercentage)}`}
              />
              
              {/* Current XP Bar */}
              <motion.div
                className={`absolute left-0 top-0 h-full bg-gradient-to-r ${getHealthBarColor(healthPercentage)} rounded-full`}
                initial={{ width: `${healthPercentage}%` }}
                animate={{ width: `${healthPercentage}%` }}
                transition={{ duration: 0.5, ease: "easeOut" }}
              />
              
              {/* Preview of XP after cost */}
              {generationCost > 0 && afterCostPercentage !== healthPercentage && (
                <motion.div
                  className={`absolute left-0 top-0 h-full bg-gradient-to-r ${getHealthBarColor(afterCostPercentage)} rounded-full opacity-50`}
                  initial={{ width: `${healthPercentage}%` }}
                  animate={{ width: `${afterCostPercentage}%` }}
                  transition={{ duration: 0.3, ease: "easeOut" }}
                />
              )}
              
              {/* Shine effect */}
              <motion.div
                className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent rounded-full"
                animate={{ x: [-100, 132] }}
                transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
              />
            </div>
            
            {/* XP Text */}
            <div className="flex items-center justify-center text-xs">
              <span className={`font-medium ${getXPStatusColor()}`}>
                {animatedXP.toLocaleString()} XP
              </span>
            </div>
          </div>
        </div>

        {/* Generation Cost Preview */}
        {generationCost > 0 && (
          <div className="flex items-center space-x-1 text-xs">
            <span className="text-gray-400">-</span>
            <span className={`font-medium ${hasInsufficientXP ? 'text-red-400' : 'text-gray-300'}`}>
              {generationCost}
            </span>
          </div>
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

      {/* Low XP warning for balance under 30% */}
      {healthPercentage < 30 && healthPercentage > 0 && !hasInsufficientXP && (
        <motion.button
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          onClick={() => router.push('/subscriptions')}
          className="flex items-center space-x-1 px-2 py-1 bg-red-500/20 rounded-full text-red-400 hover:bg-red-500/30 transition-colors"
        >
          <Plus className="w-3 h-3" />
          <span className="text-xs">Low XP</span>
        </motion.button>
      )}

      {/* Medium XP warning for balance under 60% */}
      {healthPercentage < 60 && healthPercentage >= 30 && !hasInsufficientXP && (
        <motion.button
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          onClick={() => router.push('/subscriptions')}
          className="flex items-center space-x-1 px-2 py-1 bg-orange-500/20 rounded-full text-orange-400 hover:bg-orange-500/30 transition-colors"
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