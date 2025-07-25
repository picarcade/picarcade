'use client';

import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Zap, Star, Crown, Gamepad2, TrendingUp } from 'lucide-react';

interface Subscription {
  tier_name: string;
  tier_level: number;
  tier_display_name: string;
  xp_balance: number;
  xp_allocated_this_period: number;
  xp_used_this_period: number;
  status: string;
}

interface XPBalanceProps {
  subscription: Subscription | null;
  isLoading?: boolean;
  showDetails?: boolean;
  className?: string;
}

const tierConfig = {
  1: {
    name: "Pixel Rookie",
    icon: Gamepad2,
    color: "from-green-400 to-green-600",
    textColor: "text-green-600",
    bgColor: "bg-green-50",
    borderColor: "border-green-200",
    emoji: "🎮"
  },
  2: {
    name: "Arcade Artist", 
    icon: Star,
    color: "from-blue-400 to-blue-600",
    textColor: "text-blue-600",
    bgColor: "bg-blue-50",
    borderColor: "border-blue-200",
    emoji: "🏆"
  },
  3: {
    name: "Game Master",
    icon: Crown,
    color: "from-purple-400 to-purple-600",
    textColor: "text-purple-600",
    bgColor: "bg-purple-50",
    borderColor: "border-purple-200",
    emoji: "👑"
  }
};

export default function XPBalance({ 
  subscription, 
  isLoading = false, 
  showDetails = true,
  className = ""
}: XPBalanceProps) {
  const [displayXP, setDisplayXP] = useState(0);
  const [isAnimating, setIsAnimating] = useState(false);

  const currentTier = subscription ? tierConfig[subscription.tier_level as keyof typeof tierConfig] : tierConfig[1];
  const xpBalance = subscription?.xp_balance || 0;
  const xpAllocated = subscription?.xp_allocated_this_period || 0;
  const xpUsed = subscription?.xp_used_this_period || 0;
  const usagePercentage = xpAllocated > 0 ? (xpUsed / xpAllocated) * 100 : 0;

  // Animate XP counter
  useEffect(() => {
    if (xpBalance !== displayXP) {
      setIsAnimating(true);
      const increment = Math.ceil(Math.abs(xpBalance - displayXP) / 20);
      const timer = setInterval(() => {
        setDisplayXP(prev => {
          if (prev < xpBalance) {
            const next = prev + increment;
            return next >= xpBalance ? xpBalance : next;
          } else if (prev > xpBalance) {
            const next = prev - increment;
            return next <= xpBalance ? xpBalance : next;
          }
          setIsAnimating(false);
          return prev;
        });
      }, 50);

      return () => clearInterval(timer);
    }
  }, [xpBalance, displayXP]);

  if (isLoading) {
    return (
      <div className={`bg-white rounded-xl shadow-lg border p-6 ${className}`}>
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-1/3 mb-2"></div>
          <div className="h-8 bg-gray-200 rounded w-1/2 mb-4"></div>
          <div className="h-2 bg-gray-200 rounded mb-2"></div>
          <div className="h-2 bg-gray-200 rounded w-2/3"></div>
        </div>
      </div>
    );
  }

  if (!subscription) {
    return (
      <div className={`bg-gray-50 rounded-xl border-2 border-dashed border-gray-300 p-6 text-center ${className}`}>
        <Zap className="w-8 h-8 text-gray-400 mx-auto mb-2" />
        <p className="text-gray-500 font-medium">No active subscription</p>
        <p className="text-sm text-gray-400 mt-1">Subscribe to start earning XP!</p>
      </div>
    );
  }

  const TierIcon = currentTier.icon;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className={`bg-white rounded-xl shadow-lg border-2 ${currentTier.borderColor} overflow-hidden ${className}`}
    >
      {/* Header with tier info */}
      <div className={`${currentTier.bgColor} px-6 py-4 border-b ${currentTier.borderColor}`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className={`p-2 rounded-lg bg-gradient-to-r ${currentTier.color}`}>
              <TierIcon className="w-5 h-5 text-white" />
            </div>
            <div>
              <h3 className={`font-bold ${currentTier.textColor}`}>
                {currentTier.emoji} {subscription.tier_display_name}
              </h3>
              <p className="text-sm text-gray-600">
                Subscription Active
              </p>
            </div>
          </div>
          

        </div>
      </div>

      {/* XP Balance */}
      <div className="px-6 py-4">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center space-x-2">
            <Zap className={`w-5 h-5 ${currentTier.textColor}`} />
            <span className="text-sm font-medium text-gray-600">XP Balance</span>
          </div>
          
          <motion.span
            className={`text-2xl font-bold ${currentTier.textColor}`}
            animate={isAnimating ? { scale: [1, 1.1, 1] } : {}}
            transition={{ duration: 0.3 }}
          >
            {displayXP.toLocaleString()}
          </motion.span>
        </div>

        {showDetails && (
          <>
            {/* Usage Progress Bar */}
            <div className="mb-4">
              <div className="flex justify-between items-center mb-2">
                <span className="text-xs text-gray-500">This Period Usage</span>
                <span className="text-xs text-gray-500">
                  {xpUsed.toLocaleString()} / {xpAllocated.toLocaleString()} XP
                </span>
              </div>
              
              <div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
                <motion.div
                  className={`h-full bg-gradient-to-r ${currentTier.color} rounded-full`}
                  initial={{ width: 0 }}
                  animate={{ width: `${Math.min(usagePercentage, 100)}%` }}
                  transition={{ duration: 1, ease: "easeOut" }}
                />
              </div>
              
              {usagePercentage > 90 && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="mt-2 text-xs text-amber-600 flex items-center space-x-1"
                >
                  <TrendingUp className="w-3 h-3" />
                  <span>Running low on XP this period</span>
                </motion.div>
              )}
            </div>

            {/* Quick Stats */}
            <div className="grid grid-cols-2 gap-4 pt-3 border-t border-gray-100">
              <div className="text-center">
                <p className="text-lg font-bold text-gray-800">{xpUsed.toLocaleString()}</p>
                <p className="text-xs text-gray-500">Used This Period</p>
              </div>
              <div className="text-center">
                <p className="text-lg font-bold text-gray-800">{xpAllocated.toLocaleString()}</p>
                <p className="text-xs text-gray-500">Monthly Allocation</p>
              </div>
            </div>
          </>
        )}
      </div>

      {/* Low XP Warning */}
      {xpBalance < 50 && (
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="mx-6 mb-4 p-3 bg-red-50 border border-red-200 rounded-lg"
        >
          <div className="flex items-center space-x-2">
            <Zap className="w-4 h-4 text-red-500" />
            <span className="text-sm font-medium text-red-700">Low XP Warning</span>
          </div>
                     <p className="text-xs text-red-600 mt-1">
             You&apos;re running low on XP. Consider upgrading your tier or wait for next month&apos;s allocation.
           </p>
        </motion.div>
      )}
    </motion.div>
  );
} 