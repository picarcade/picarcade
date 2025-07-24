'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { 
  Star, Crown, Gamepad2, Check
} from 'lucide-react';

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

interface SubscriptionTiersProps {
  tiers: Tier[];
  currentTier?: number;
  onSelectTier: (tier: Tier) => void;
  isLoading?: boolean;
  className?: string;
}

const tierConfig = {
  1: {
    name: "Pixel Rookie",
    icon: Gamepad2,
    textColor: "text-green-400",
    borderColor: "border-gray-600",
    buttonColor: "bg-blue-500 hover:bg-blue-600",
    planType: "Gaming Starter",
    price: 15, // AUD from documentation
    xp: 600 // XP from documentation
  },
  2: {
    name: "Arcade Artist",
    icon: Star,
    textColor: "text-blue-400",
    borderColor: "border-gray-600",
    buttonColor: "bg-blue-500 hover:bg-blue-600",
    planType: "Creative Pro",
    price: 20, // AUD from documentation
    xp: 800 // XP from documentation
  },
  3: {
    name: "Game Master",
    icon: Crown,
    textColor: "text-purple-400",
    borderColor: "border-gray-600",
    buttonColor: "bg-blue-500 hover:bg-blue-600",
    planType: "Ultimate Power",
    price: 33, // AUD from documentation
    xp: 1320 // XP from documentation
  }
};

export default function SubscriptionTiers({
  tiers,
  currentTier,
  onSelectTier,
  isLoading = false,
  className = ""
}: SubscriptionTiersProps) {
  // Sort tiers by level
  const sortedTiers = [...tiers].sort((a, b) => a.tier_level - b.tier_level);

  const getFeatureList = (tier: Tier) => {
    const config = tierConfig[tier.tier_level as keyof typeof tierConfig];
    const features = [];
    
    // XP Allocation from documentation
    features.push(`${config.xp.toLocaleString()} XP credits`);

    // Generation types
    if (tier.generation_types_allowed.includes('NEW_IMAGE')) {
      features.push('AI Image Generation');
    }

    if (tier.generation_types_allowed.includes('NEW_VIDEO')) {
      features.push('AI Video Generation');
    }

    if (tier.generation_types_allowed.includes('EDIT_IMAGE')) {
      features.push('Advanced Image Editing');
    }

    // AI Models
    features.push(`Access to ${tier.ai_models_included.length} AI Models`);

    // Advanced features for higher tiers
    if (tier.tier_level >= 2) {
      features.push('Premium Model Access');
    }

    if (tier.tier_level >= 3) {
      features.push('Premium Support');
      features.push('Advanced Features');
    }

    return features;
  };

  if (isLoading) {
    return (
      <div className={`grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6 max-w-7xl mx-auto px-4 sm:px-0 ${className}`}>
        {[1, 2, 3].map((i) => (
          <div key={i} className="bg-gray-800/50 rounded-xl border border-gray-700 p-4 sm:p-6 animate-pulse">
            <div className="h-4 bg-gray-700 rounded w-1/2 mb-4"></div>
            <div className="h-8 bg-gray-700 rounded w-1/3 mb-6"></div>
            <div className="space-y-3">
              {[1, 2, 3, 4].map((j) => (
                <div key={j} className="h-3 bg-gray-700 rounded"></div>
              ))}
            </div>
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className={`grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6 max-w-7xl mx-auto px-4 sm:px-0 ${className}`}>
      {sortedTiers.map((tier) => {
        const config = tierConfig[tier.tier_level as keyof typeof tierConfig];
        const features = getFeatureList(tier);
        const price = config.price;
        const currencySymbol = 'A$';
        const isCurrentTier = currentTier === tier.tier_level;

        return (
          <motion.div
            key={tier.id}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: tier.tier_level * 0.1 }}
            whileHover={{ y: -4, transition: { duration: 0.2 } }}
            className={`relative rounded-xl overflow-hidden cursor-pointer transition-all duration-300 border-2 bg-gray-800/80 backdrop-blur-sm ${config.borderColor} flex flex-col`}
            onClick={() => {
              onSelectTier(tier);
            }}
          >
            {/* Current Tier Badge */}
            {isCurrentTier && (
              <div className="absolute -top-2 sm:-top-3 right-2 sm:right-4 z-10">
                <div className="px-2 sm:px-3 py-1 bg-gradient-to-r from-yellow-400 to-yellow-500 text-yellow-900 rounded-full text-xs font-bold">
                  CURRENT
                </div>
              </div>
            )}

            <div className="p-4 sm:p-6 flex flex-col flex-grow">
              {/* Tier Name */}
              <div className="text-center mb-4 sm:mb-6">
                <h3 className="text-lg sm:text-xl font-bold text-white mb-2 sm:mb-4">
                  {config.name}
                </h3>
                
                {/* Price */}
                <div className="mb-4 sm:mb-6">
                  <span className="text-2xl sm:text-4xl font-bold text-white">
                    {currencySymbol}{price}
                  </span>
                  <span className="text-gray-400 text-xs sm:text-sm ml-1">/month</span>
                </div>
              </div>

              {/* Features */}
              <div className="space-y-2 sm:space-y-3 mb-6 sm:mb-8 text-left flex-grow">
                {features.map((feature, index) => (
                  <div
                    key={index}
                    className="flex items-center space-x-2 sm:space-x-3"
                  >
                    <Check className="w-3 sm:w-4 h-3 sm:h-4 text-gray-400 flex-shrink-0" />
                    <span className="text-gray-300 text-xs sm:text-sm">
                      {feature}
                    </span>
                  </div>
                ))}
              </div>

              {/* Action Button - This will be at the bottom due to flex-grow above */}
              <button
                className={`w-full py-2 sm:py-3 px-4 sm:px-6 rounded-lg font-medium transition-all duration-200 mt-auto text-sm sm:text-base ${
                  isCurrentTier
                    ? 'bg-gray-600 text-gray-400 cursor-not-allowed'
                    : 'bg-gray-100 text-gray-900 hover:bg-white hover:shadow-sm'
                }`}
                disabled={isCurrentTier}
              >
                {isCurrentTier ? 'Current Plan' : 'Choose Plan'}
              </button>
            </div>
          </motion.div>
        );
      })}
    </div>
  );
} 