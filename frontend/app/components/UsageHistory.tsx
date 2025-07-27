import React, { useState, useEffect } from 'react';
import { Clock, Zap, Calendar, ChevronLeft, ChevronRight, Search } from 'lucide-react';

interface XPTransaction {
  id: string;
  transaction_type: string;
  amount: number;
  balance_after: number;
  generation_type?: string;
  model_used?: string;
  description?: string;
  created_at: string;
}

interface UsageHistoryProps {
  className?: string;
}

export default function UsageHistory({ className = "" }: UsageHistoryProps) {
  const [transactions, setTransactions] = useState<XPTransaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterType, setFilterType] = useState<string>('all');
  const [currentPage, setCurrentPage] = useState(1);
  const [error, setError] = useState<string | null>(null);

  const itemsPerPage = 10;

  useEffect(() => {
    loadTransactions();
  }, []);

  const loadTransactions = async () => {
    setLoading(true);
    setError(null);
    try {
      const token = localStorage.getItem('access_token');
      const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      
      const response = await fetch(`${baseUrl}/api/v1/subscriptions/xp/transactions?limit=100`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        throw new Error('Failed to fetch transaction history');
      }

      const data = await response.json();
      // Filter to only show deductions (actual usage)
      const usageTransactions = data.filter((t: XPTransaction) => t.transaction_type === 'deduction');
      setTransactions(usageTransactions);
    } catch (error) {
      console.error('Error loading transactions:', error);
      setError('Failed to load usage history');
      setTransactions([]);
    } finally {
      setLoading(false);
    }
  };

  const extractPromptFromDescription = (description: string | undefined): string => {
    if (!description) return 'N/A';
    
    // If description starts with "Generation:" it's the old format, try to extract
    if (description.startsWith('Generation:')) {
      const match = description.match(/Generation: (.+) using/);
      if (match) {
        return match[1];
      }
      return description;
    }
    
    // Otherwise it's likely the actual prompt, truncate for display if needed
    return description.length > 100 ? `${description.substring(0, 100)}...` : description;
  };

  const filteredTransactions = transactions.filter(transaction => {
    const matchesSearch = searchTerm === '' || 
      transaction.description?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      transaction.model_used?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      transaction.generation_type?.toLowerCase().includes(searchTerm.toLowerCase());

    const matchesFilter = filterType === 'all' || transaction.generation_type === filterType;

    return matchesSearch && matchesFilter;
  });

  const totalPages = Math.ceil(filteredTransactions.length / itemsPerPage);
  const startIndex = (currentPage - 1) * itemsPerPage;
  const paginatedTransactions = filteredTransactions.slice(startIndex, startIndex + itemsPerPage);

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-AU', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const uniqueGenerationTypes = [...new Set(transactions.map(t => t.generation_type).filter(Boolean))];

  if (loading) {
    return (
      <div className={`bg-gray-800/60 backdrop-blur-sm border border-gray-700/50 rounded-2xl p-6 ${className}`}>
        <div className="animate-pulse">
          <div className="h-8 bg-gray-700 rounded w-1/3 mb-6"></div>
          <div className="space-y-3">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-16 bg-gray-700/50 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`bg-gray-800/60 backdrop-blur-sm border border-gray-700/50 rounded-2xl p-6 ${className}`}>
        <div className="text-center py-12">
          <Clock className="w-12 h-12 text-red-400 mx-auto mb-4" />
          <h3 className="text-xl font-bold text-white mb-2">Error Loading Usage History</h3>
          <p className="text-gray-400 mb-6">{error}</p>
          <button
            onClick={loadTransactions}
            className="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className={`bg-gray-800/60 backdrop-blur-sm border border-gray-700/50 rounded-2xl p-6 ${className}`}>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-3xl font-bold text-white">Usage History</h2>
        <div className="flex items-center space-x-3">
          <div className="relative">
            <Search className="w-4 h-4 text-gray-400 absolute left-3 top-1/2 transform -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search prompts, models..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-10 pr-4 py-2 bg-gray-700/50 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:border-blue-500 focus:outline-none"
            />
          </div>
          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
            className="px-3 py-2 bg-gray-700/50 border border-gray-600 rounded-lg text-white focus:border-blue-500 focus:outline-none"
          >
            <option value="all">All Types</option>
            {uniqueGenerationTypes.map(type => (
              <option key={type} value={type}>
                {type?.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()) || 'Unknown'}
              </option>
            ))}
          </select>
        </div>
      </div>

      {filteredTransactions.length === 0 ? (
                 <div className="text-center py-16">
           <Zap className="w-12 h-12 text-gray-400 mx-auto mb-4" />
           <h3 className="text-xl font-bold text-white mb-2">No Usage Records</h3>
           <p className="text-gray-400 text-lg">
             {transactions.length === 0 
               ? "You haven't used any XP yet. Start generating to see your usage history!" 
               : "No records match your current filters."
             }
           </p>
         </div>
      ) : (
        <>
          {/* Header */}
          <div className="hidden md:grid grid-cols-10 gap-4 text-sm font-medium text-gray-400 border-b border-gray-700 pb-3 mb-4">
            <div className="col-span-3">Timestamp</div>
            <div className="col-span-5">Prompt</div>
            <div className="col-span-1">Model Used</div>
            <div className="col-span-1 text-right">XP Used</div>
          </div>

          {/* Transaction List */}
          <div className="space-y-3">
            {paginatedTransactions.map((transaction) => (
              <div
                key={transaction.id}
                className="bg-gray-700/30 border border-gray-600/50 rounded-lg p-4 hover:bg-gray-700/50 transition-colors"
              >
                <div className="grid grid-cols-1 md:grid-cols-10 gap-4 items-start">
                  {/* Timestamp */}
                  <div className="md:col-span-3">
                    <div className="flex items-center space-x-2 text-sm text-gray-300">
                      <Calendar className="w-4 h-4 text-gray-400" />
                      <span>{formatDate(transaction.created_at)}</span>
                    </div>
                  </div>

                  {/* Prompt */}
                  <div className="md:col-span-5">
                    <p className="text-white text-sm">
                      {extractPromptFromDescription(transaction.description)}
                    </p>
                  </div>

                  {/* Model Used */}
                  <div className="md:col-span-1">
                    <span className="text-sm text-gray-300 font-mono">
                      {transaction.model_used || 'N/A'}
                    </span>
                  </div>

                  {/* XP Used */}
                  <div className="md:col-span-1 md:text-right">
                    <span className="text-white font-semibold">
                      {Math.abs(transaction.amount)}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between mt-6 pt-4 border-t border-gray-700">
              <div className="text-sm text-gray-400">
                Showing {startIndex + 1}-{Math.min(startIndex + itemsPerPage, filteredTransactions.length)} of {filteredTransactions.length} records
              </div>
              
              <div className="flex items-center space-x-2">
                <button
                  onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                  disabled={currentPage === 1}
                  className="p-2 rounded-lg bg-gray-700/50 text-gray-400 hover:text-white hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
                
                <span className="text-sm text-gray-300">
                  Page {currentPage} of {totalPages}
                </span>
                
                <button
                  onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
                  disabled={currentPage === totalPages}
                  className="p-2 rounded-lg bg-gray-700/50 text-gray-400 hover:text-white hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
} 