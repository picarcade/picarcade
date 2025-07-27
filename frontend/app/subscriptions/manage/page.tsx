'use client';

import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { 
  ArrowLeft, Settings, CreditCard, Calendar, Download,
  AlertTriangle, CheckCircle, XCircle,
  Trash2, Edit, Plus, DollarSign, TrendingUp, Zap, X
} from 'lucide-react';
import { useRouter } from 'next/navigation';
import dynamic from 'next/dynamic';
import XPBalance from '../../components/XPBalance';
import UsageHistory from '../../components/UsageHistory';

// Dynamically import components to avoid SSR issues
const PaymentModal = dynamic(() => import('../../components/PaymentModal'), { ssr: false });

interface Subscription {
  id: string;
  tier_name: string;
  tier_level: number;
  tier_display_name: string;
  xp_balance: number;
  xp_allocated_this_period: number;
  xp_used_this_period: number;
  status: string;
  current_period_start: string;
  current_period_end: string;

  stripe_subscription_id?: string;
  stripe_customer_id?: string;
}

interface Invoice {
  id: string;
  amount_paid: number;
  currency: string;
  status: string;
  created: number;
  invoice_pdf?: string;
  hosted_invoice_url?: string;
  period_start: number;
  period_end: number;
}

interface PaymentMethod {
  id: string;
  type: string;
  card?: {
    brand: string;
    last4: string;
    exp_month: number;
    exp_year: number;
  };
  is_default: boolean;
}

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

export default function SubscriptionManagePage() {
  const router = useRouter();
  const [subscription, setSubscription] = useState<Subscription | null>(null);
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [paymentMethods, setPaymentMethods] = useState<PaymentMethod[]>([]);
  const [tiers, setTiers] = useState<Tier[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [showCancelModal, setShowCancelModal] = useState(false);
  const [showChangeModal, setShowChangeModal] = useState(false);
  const [selectedTier, setSelectedTier] = useState<Tier | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'billing' | 'usage'>('overview');

  type TabType = 'overview' | 'billing' | 'usage';

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

      // Load current subscription
      const subResponse = await fetch(`${baseUrl}/api/v1/subscriptions/current`, { headers });
      if (subResponse.ok) {
        const subData = await subResponse.json();
        setSubscription(subData);
      }

      // Load tiers for plan changes
      const tiersResponse = await fetch(`${baseUrl}/api/v1/subscriptions/tiers`, { headers });
      if (tiersResponse.ok) {
        const tiersData = await tiersResponse.json();
        setTiers(tiersData);
      }

      // Load billing history
      try {
        const invoicesResponse = await fetch(`${baseUrl}/api/v1/subscriptions/invoices`, { headers });
        if (invoicesResponse.ok) {
          const invoicesData = await invoicesResponse.json();
          setInvoices(invoicesData);
        }
      } catch (error) {
        console.log('Invoices not loaded:', error);
      }

      // Load payment methods
      try {
        const pmResponse = await fetch(`${baseUrl}/api/v1/subscriptions/payment-methods`, { headers });
        if (pmResponse.ok) {
          const pmData = await pmResponse.json();
          setPaymentMethods(pmData);
        }
      } catch (error) {
        console.log('Payment methods not loaded:', error);
      }

    } catch (error) {
      console.error('Error loading subscription data:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCancelSubscription = async () => {
    if (!subscription) return;
    
    setActionLoading('cancel');
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch('/api/v1/subscriptions/cancel', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        await loadSubscriptionData();
        setShowCancelModal(false);
      }
    } catch (error) {
      console.error('Error canceling subscription:', error);
    } finally {
      setActionLoading(null);
    }
  };

  const handleChangePlan = (tier: Tier) => {
    setSelectedTier(tier);
    setShowChangeModal(true);
  };

  const formatDate = (timestamp: number) => {
    return new Date(timestamp * 1000).toLocaleDateString();
  };

  const formatCurrency = (amount: number, currency: string) => {
    const symbol = currency === 'usd' ? '$' : currency === 'aud' ? 'A$' : currency.toUpperCase();
    return `${symbol}${(amount / 100).toFixed(2)}`;
  };

  const getStatusBadge = (status: string) => {
    const statusConfig = {
      active: { icon: CheckCircle, color: 'text-green-600 bg-green-50 border-green-200', text: 'Active' },
    
      canceled: { icon: XCircle, color: 'text-red-600 bg-red-50 border-red-200', text: 'Canceled' },
      past_due: { icon: AlertTriangle, color: 'text-yellow-600 bg-yellow-50 border-yellow-200', text: 'Past Due' }
    };

    const config = statusConfig[status as keyof typeof statusConfig] || statusConfig.active;
    const Icon = config.icon;

    return (
      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${config.color}`}>
        <Icon className="w-3 h-3 mr-1" />
        {config.text}
      </span>
    );
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 py-8">
        <div className="max-w-4xl mx-auto px-4">
          <div className="animate-pulse">
            <div className="h-8 bg-gray-700 rounded w-1/3 mb-8"></div>
            <div className="space-y-4">
              <div className="h-32 bg-gray-700 rounded"></div>
              <div className="h-64 bg-gray-700 rounded"></div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 py-8">
      <div className="max-w-4xl mx-auto px-4">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center space-x-4">
            <button
              onClick={() => router.back()}
              className="p-2 hover:bg-gray-700/50 rounded-lg transition-colors"
            >
              <ArrowLeft className="w-5 h-5 text-white" />
            </button>
            <div>
              <h1 className="text-3xl font-bold text-white">Subscription Management</h1>
              <p className="text-gray-400">Manage your subscription, billing, and usage</p>
            </div>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div className="flex space-x-1 bg-gray-800/50 rounded-lg p-1 mb-8">
          {[
            { id: 'overview', label: 'Overview', icon: Settings },
            { id: 'billing', label: 'Billing', icon: CreditCard },
            { id: 'usage', label: 'Usage', icon: TrendingUp }
          ].map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as TabType)}
                className={`flex items-center space-x-2 px-4 py-2 rounded-lg transition-colors ${
                  activeTab === tab.id
                    ? 'bg-gray-700 text-white'
                    : 'text-gray-400 hover:text-white hover:bg-gray-700/50'
                }`}
              >
                <Icon className="w-4 h-4" />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>

        {/* Overview Tab */}
        {activeTab === 'overview' && (
          <div className="space-y-6">
            {/* Current Subscription */}
            <div className="bg-gray-800/60 backdrop-blur-sm border border-gray-700/50 rounded-2xl p-6">
              <h2 className="text-xl font-bold text-white mb-4">Current Subscription</h2>
              
              {subscription ? (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="text-lg font-semibold text-white">
                        {subscription.tier_display_name}
                      </h3>
                      {getStatusBadge(subscription.status)}
                    </div>
                    
                    <div className="space-y-2 text-sm text-gray-300">
                      <div>Next billing: {formatDate(new Date(subscription.current_period_end).getTime() / 1000)}</div>
                      
                    </div>

                    <div className="flex space-x-3 mt-6">
                      <button
                        onClick={() => setShowChangeModal(true)}
                        className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
                      >
                        Change Plan
                      </button>
                      
                      {subscription.status === 'active' && (
                        <button
                          onClick={() => setShowCancelModal(true)}
                          className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors"
                        >
                          Cancel Subscription
                        </button>
                      )}
                    </div>
                  </div>

                  <div>
                    <XPBalance 
                      subscription={subscription} 
                      showDetails={true}
                      className="h-full"
                    />
                  </div>
                </div>
              ) : (
                <div className="text-center py-8">
                  <Zap className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                  <h3 className="text-lg font-semibold text-white mb-2">No Active Subscription</h3>
                  <p className="text-gray-400 mb-4">Subscribe to unlock premium features and XP credits</p>
                  <button
                    onClick={() => router.push('/subscriptions')}
                    className="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
                  >
                    View Plans
                  </button>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Billing Tab */}
        {activeTab === 'billing' && (
          <div className="space-y-6">
            {/* Payment Methods */}
            <div className="bg-gray-800/60 backdrop-blur-sm border border-gray-700/50 rounded-2xl p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-bold text-white">Payment Methods</h2>
                <button className="flex items-center space-x-2 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors">
                  <Plus className="w-4 h-4" />
                  <span>Add Payment Method</span>
                </button>
              </div>

              {paymentMethods.length > 0 ? (
                <div className="space-y-3">
                  {paymentMethods.map((method) => (
                    <div key={method.id} className="flex items-center justify-between p-4 bg-gray-700/50 rounded-lg">
                      <div className="flex items-center space-x-3">
                        <CreditCard className="w-5 h-5 text-gray-400" />
                        <div>
                          <div className="text-white">
                            {method.card?.brand.toUpperCase()} ****{method.card?.last4}
                          </div>
                          <div className="text-sm text-gray-400">
                            Expires {method.card?.exp_month}/{method.card?.exp_year}
                            {method.is_default && <span className="ml-2 text-blue-400">• Default</span>}
                          </div>
                        </div>
                      </div>
                      
                      <div className="flex items-center space-x-2">
                        <button className="p-2 text-gray-400 hover:text-white transition-colors">
                          <Edit className="w-4 h-4" />
                        </button>
                        <button className="p-2 text-gray-400 hover:text-red-400 transition-colors">
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8 text-gray-400">
                  <CreditCard className="w-12 h-12 mx-auto mb-4" />
                  <p>No payment methods added</p>
                </div>
              )}
            </div>

            {/* Billing History */}
            <div className="bg-gray-800/60 backdrop-blur-sm border border-gray-700/50 rounded-2xl p-6">
              <h2 className="text-xl font-bold text-white mb-4">Billing History</h2>
              
              {invoices.length > 0 ? (
                <div className="space-y-3">
                  {invoices.map((invoice) => (
                    <div key={invoice.id} className="flex items-center justify-between p-4 bg-gray-700/50 rounded-lg">
                      <div className="flex items-center space-x-3">
                        <Calendar className="w-5 h-5 text-gray-400" />
                        <div>
                          <div className="text-white">
                            {formatCurrency(invoice.amount_paid, invoice.currency)} - {invoice.status}
                          </div>
                          <div className="text-sm text-gray-400">
                            {formatDate(invoice.created)} • 
                            Period: {formatDate(invoice.period_start)} - {formatDate(invoice.period_end)}
                          </div>
                        </div>
                      </div>
                      
                      <div className="flex items-center space-x-2">
                        {invoice.hosted_invoice_url && (
                          <a
                            href={invoice.hosted_invoice_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="p-2 text-gray-400 hover:text-white transition-colors"
                          >
                            <Download className="w-4 h-4" />
                          </a>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8 text-gray-400">
                  <DollarSign className="w-12 h-12 mx-auto mb-4" />
                  <p>No billing history available</p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Usage Tab */}
        {activeTab === 'usage' && subscription && (
          <div className="space-y-6">
            <XPBalance 
              subscription={subscription} 
              showDetails={true}
            />
            
            {/* Usage History */}
            <UsageHistory />
          </div>
        )}

        {/* Cancel Subscription Modal */}
        {showCancelModal && (
          <div className="fixed inset-0 z-50 overflow-y-auto">
            <div className="flex items-center justify-center min-h-screen px-4">
              <div className="fixed inset-0 bg-black bg-opacity-50" onClick={() => setShowCancelModal(false)}></div>
              
              <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                className="relative bg-white rounded-2xl p-6 max-w-md w-full"
              >
                <h3 className="text-lg font-bold text-gray-900 mb-4">Cancel Subscription</h3>
                <p className="text-gray-600 mb-6">
                                     Are you sure you want to cancel your subscription? You&apos;ll lose access to premium features at the end of your current billing period.
                </p>
                
                <div className="flex space-x-3">
                  <button
                    onClick={handleCancelSubscription}
                    disabled={actionLoading === 'cancel'}
                    className="flex-1 bg-red-500 text-white py-2 px-4 rounded-lg hover:bg-red-600 disabled:opacity-50 transition-colors"
                  >
                    {actionLoading === 'cancel' ? 'Canceling...' : 'Yes, Cancel'}
                  </button>
                  <button
                    onClick={() => setShowCancelModal(false)}
                    className="flex-1 bg-gray-200 text-gray-800 py-2 px-4 rounded-lg hover:bg-gray-300 transition-colors"
                  >
                    Keep Subscription
                  </button>
                </div>
              </motion.div>
            </div>
          </div>
        )}

        {/* Change Plan Modal */}
        {showChangeModal && (
          <div className="fixed inset-0 z-50 overflow-y-auto">
            <div className="flex items-center justify-center min-h-screen px-4">
              <div className="fixed inset-0 bg-black bg-opacity-50" onClick={() => setShowChangeModal(false)}></div>
              
              <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                className="relative bg-white rounded-2xl p-6 max-w-2xl w-full max-h-[80vh] overflow-y-auto"
              >
                <div className="flex items-center justify-between mb-6">
                  <h3 className="text-lg font-bold text-gray-900">Change Subscription Plan</h3>
                  <button
                    onClick={() => setShowChangeModal(false)}
                    className="p-2 hover:bg-gray-100 rounded-lg"
                  >
                    <X className="w-5 h-5" />
                  </button>
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {tiers.map((tier) => (
                    <div
                      key={tier.id}
                      className={`border-2 rounded-lg p-4 cursor-pointer transition-colors ${
                        subscription?.tier_level === tier.tier_level
                          ? 'border-blue-500 bg-blue-50'
                          : 'border-gray-200 hover:border-gray-300'
                      }`}
                      onClick={() => handleChangePlan(tier)}
                    >
                      <h4 className="font-semibold text-gray-900">{tier.tier_display_name}</h4>
                      <p className="text-2xl font-bold text-gray-900 mt-2">
                        A${tier.monthly_price_aud}<span className="text-sm font-normal">/month</span>
                      </p>
                      <p className="text-sm text-gray-600 mt-2">{tier.monthly_xp_allocation.toLocaleString()} XP/month</p>
                      
                      {subscription?.tier_level === tier.tier_level && (
                        <span className="inline-block mt-2 text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded">
                          Current Plan
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              </motion.div>
            </div>
          </div>
        )}

        {/* Payment Modal for Plan Changes */}
        {selectedTier && (
          <PaymentModal
            isOpen={!!selectedTier}
            onClose={() => {
              setSelectedTier(null);
              setShowChangeModal(false);
            }}
            selectedTier={selectedTier}
            currentTier={subscription?.tier_level}
            currency="aud"
            onSuccess={() => {
              setSelectedTier(null);
              setShowChangeModal(false);
              loadSubscriptionData();
            }}
          />
        )}
      </div>
    </div>
  );
} 