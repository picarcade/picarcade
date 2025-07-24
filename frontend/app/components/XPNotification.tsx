'use client';

import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { TrendingUp, TrendingDown, Gift, RotateCcw } from 'lucide-react';

interface XPNotificationProps {
  isVisible: boolean;
  amount: number;
  type: 'gain' | 'loss' | 'bonus' | 'refund';
  reason?: string;
  onComplete?: () => void;
  duration?: number;
}

const typeConfig = {
  gain: {
    icon: TrendingUp,
    color: 'text-green-500',
    bgColor: 'bg-green-50',
    borderColor: 'border-green-200',
    prefix: '+',
    emoji: '💎'
  },
  loss: {
    icon: TrendingDown,
    color: 'text-red-500',
    bgColor: 'bg-red-50',
    borderColor: 'border-red-200',
    prefix: '-',
    emoji: '⚡'
  },
  bonus: {
    icon: Gift,
    color: 'text-purple-500',
    bgColor: 'bg-purple-50',
    borderColor: 'border-purple-200',
    prefix: '+',
    emoji: '🎁'
  },
  refund: {
    icon: RotateCcw,
    color: 'text-blue-500',
    bgColor: 'bg-blue-50',
    borderColor: 'border-blue-200',
    prefix: '+',
    emoji: '↩️'
  }
};

export default function XPNotification({ 
  isVisible, 
  amount, 
  type, 
  reason, 
  onComplete, 
  duration = 3000 
}: XPNotificationProps) {
  const [show, setShow] = useState(false);
  const config = typeConfig[type];
  const Icon = config.icon;

  useEffect(() => {
    if (isVisible) {
      setShow(true);
      
      const timer = setTimeout(() => {
        setShow(false);
        setTimeout(() => {
          onComplete?.();
        }, 300); // Wait for exit animation
      }, duration);

      return () => clearTimeout(timer);
    }
  }, [isVisible, duration, onComplete]);

  return (
    <AnimatePresence>
      {show && (
        <motion.div
          initial={{ opacity: 0, y: -50, scale: 0.9 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: -20, scale: 0.95 }}
          transition={{ 
            type: "spring", 
            stiffness: 500, 
            damping: 30 
          }}
          className="fixed top-4 right-4 z-50"
        >
          <motion.div
            animate={{ 
              scale: [1, 1.05, 1],
            }}
            transition={{ 
              duration: 0.6,
              times: [0, 0.3, 1],
              ease: "easeInOut"
            }}
            className={`${config.bgColor} ${config.borderColor} border-2 rounded-xl shadow-lg p-4 min-w-[280px]`}
          >
            <div className="flex items-center space-x-3">
              {/* Animated Icon */}
              <motion.div
                initial={{ rotate: 0 }}
                animate={{ rotate: [0, 15, -15, 0] }}
                transition={{ duration: 0.5, delay: 0.2 }}
                className={`p-2 rounded-lg ${config.bgColor} border ${config.borderColor}`}
              >
                <Icon className={`w-5 h-5 ${config.color}`} />
              </motion.div>

              {/* Content */}
              <div className="flex-1">
                <div className="flex items-center space-x-2">
                  <span className="text-lg">{config.emoji}</span>
                  <motion.span
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    transition={{ delay: 0.1, type: "spring" }}
                    className={`text-lg font-bold ${config.color}`}
                  >
                    {config.prefix}{Math.abs(amount)} XP
                  </motion.span>
                </div>
                
                {reason && (
                  <motion.p
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.3 }}
                    className="text-sm text-gray-600 mt-1"
                  >
                    {reason}
                  </motion.p>
                )}
              </div>

              {/* Sparkle Effect */}
              <motion.div
                initial={{ opacity: 0, scale: 0 }}
                animate={{ opacity: [0, 1, 0], scale: [0, 1.2, 0] }}
                transition={{ duration: 1, delay: 0.5 }}
                className="text-2xl"
              >
                ✨
              </motion.div>
            </div>

            {/* Progress Bar */}
            <motion.div
              className="mt-3 h-1 bg-gray-200 rounded-full overflow-hidden"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.4 }}
            >
              <motion.div
                className={`h-full ${config.color.replace('text-', 'bg-')}`}
                initial={{ width: '100%' }}
                animate={{ width: '0%' }}
                transition={{ duration: duration / 1000, ease: "linear" }}
              />
            </motion.div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

// Hook for managing XP notifications
export function useXPNotifications() {
  const [notifications, setNotifications] = useState<Array<{
    id: string;
    amount: number;
    type: 'gain' | 'loss' | 'bonus' | 'refund';
    reason?: string;
  }>>([]);

  const showNotification = (
    amount: number, 
    type: 'gain' | 'loss' | 'bonus' | 'refund', 
    reason?: string
  ) => {
    const id = Math.random().toString(36).substr(2, 9);
    setNotifications(prev => [...prev, { id, amount, type, reason }]);
  };

  const removeNotification = (id: string) => {
    setNotifications(prev => prev.filter(n => n.id !== id));
  };

  const NotificationContainer = () => (
    <div className="fixed top-4 right-4 z-50 space-y-2">
      {notifications.map((notification, index) => (
        <motion.div
          key={notification.id}
          initial={{ opacity: 0, x: 300 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: index * 0.1 }}
        >
          <XPNotification
            isVisible={true}
            amount={notification.amount}
            type={notification.type}
            reason={notification.reason}
            onComplete={() => removeNotification(notification.id)}
          />
        </motion.div>
      ))}
    </div>
  );

  return {
    showNotification,
    NotificationContainer
  };
} 