/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
/**
 * QuickAddRecent - Shows recently added items for quick re-adding
 * Displays items that were recently added to orders for fast repeat selection
 */
import React, { useState } from 'react';
import {
  FaClock,
  FaPlus,
  FaStar,
  FaHistory,
  FaChevronRight,
  FaChevronDown
} from 'react-icons/fa';
import { formatCurrency } from '@/utils/stringUtils';

interface RecentItem {
  id: number;
  itemCode: string;
  description: string;
  lastUsed: string;
  usageCount: number;
  lastQuantity?: number;
  lastPrice?: number;
}

interface QuickAddRecentProps {
  recentItems?: RecentItem[];
  favoriteItems?: RecentItem[];
  onAddItem?: (item: RecentItem, quantity?: number) => void;
  isVisible?: boolean;
}

// Demo recent items
const demoRecentItems: RecentItem[] = [
  {
    id: 1,
    itemCode: 'WIDGET-001',
    description: 'Standard Widget Assembly',
    lastUsed: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
    usageCount: 15,
    lastQuantity: 10,
    lastPrice: 25.99,
  },
  {
    id: 2,
    itemCode: 'GADGET-002',
    description: 'Premium Gadget Kit',
    lastUsed: new Date(Date.now() - 5 * 60 * 60 * 1000).toISOString(),
    usageCount: 8,
    lastQuantity: 5,
    lastPrice: 149.99,
  },
  {
    id: 3,
    itemCode: 'PART-003',
    description: 'Replacement Part XL',
    lastUsed: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
    usageCount: 22,
    lastQuantity: 100,
    lastPrice: 3.50,
  },
];

const demoFavorites: RecentItem[] = [
  {
    id: 4,
    itemCode: 'BOLT-SS-10',
    description: 'Stainless Steel Bolt 10mm',
    lastUsed: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString(),
    usageCount: 50,
    lastQuantity: 500,
    lastPrice: 0.25,
  },
  {
    id: 5,
    itemCode: 'WASHER-FL',
    description: 'Flat Washer Standard',
    lastUsed: new Date(Date.now() - 5 * 24 * 60 * 60 * 1000).toISOString(),
    usageCount: 45,
    lastQuantity: 1000,
    lastPrice: 0.10,
  },
];

const QuickAddRecent: React.FC<QuickAddRecentProps> = ({
  recentItems = demoRecentItems,
  favoriteItems = demoFavorites,
  onAddItem,
  isVisible = true,
}) => {
  const [showRecent, setShowRecent] = useState(true);
  const [showFavorites, setShowFavorites] = useState(true);

  if (!isVisible) return null;

  // Format relative time
  const formatTimeAgo = (dateString: string) => {
    const diff = Date.now() - new Date(dateString).getTime();
    const hours = Math.floor(diff / (60 * 60 * 1000));
    const days = Math.floor(hours / 24);
    
    if (days > 0) return `${days}d ago`;
    if (hours > 0) return `${hours}h ago`;
    return 'Just now';
  };


  // Render item row
  const renderItem = (item: RecentItem) => (
    <div 
      key={item.id}
      className="flex items-center justify-between p-2 hover:bg-slate-50 dark:hover:bg-slate-800/50 rounded-lg cursor-pointer group"
      onClick={() => onAddItem?.(item, item.lastQuantity)}
    >
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-slate-900 dark:text-white truncate">
          {item.itemCode}
        </p>
        <p className="text-xs text-slate-500 dark:text-slate-400 truncate">
          {item.description}
        </p>
      </div>
      
      <div className="flex items-center gap-3">
        {item.lastQuantity && (
          <span className="text-xs text-slate-400 dark:text-slate-500">
            x{item.lastQuantity}
          </span>
        )}
        {item.lastPrice && (
          <span className="text-xs text-slate-500 dark:text-slate-400">
            {formatCurrency(item.lastPrice)}
          </span>
        )}
        <button
          className="p-1 text-slate-400 group-hover:text-blue-500 opacity-0 group-hover:opacity-100 transition-all"
          title="Add to order"
        >
          <FaPlus size={12} />
        </button>
      </div>
    </div>
  );

  return (
    <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg overflow-hidden">
      {/* Recent Items Section */}
      <div>
        <button
          onClick={() => setShowRecent(!showRecent)}
          className="flex items-center justify-between w-full px-4 py-3 text-left hover:bg-slate-50 dark:hover:bg-slate-800/50"
        >
          <div className="flex items-center gap-2">
            <FaHistory className="text-slate-400" size={14} />
            <span className="text-sm font-medium text-slate-700 dark:text-slate-300">
              Recent Items
            </span>
            <span className="text-xs text-slate-400 dark:text-slate-500">
              ({recentItems.length})
            </span>
          </div>
          {showRecent ? (
            <FaChevronDown className="text-slate-400" size={12} />
          ) : (
            <FaChevronRight className="text-slate-400" size={12} />
          )}
        </button>
        
        {showRecent && (
          <div className="px-2 pb-2">
            {recentItems.length === 0 ? (
              <p className="px-2 py-3 text-sm text-slate-400 dark:text-slate-500 text-center">
                No recent items
              </p>
            ) : (
              recentItems.map(renderItem)
            )}
          </div>
        )}
      </div>

      {/* Divider */}
      <div className="border-t border-slate-200 dark:border-slate-700"></div>

      {/* Favorites Section */}
      <div>
        <button
          onClick={() => setShowFavorites(!showFavorites)}
          className="flex items-center justify-between w-full px-4 py-3 text-left hover:bg-slate-50 dark:hover:bg-slate-800/50"
        >
          <div className="flex items-center gap-2">
            <FaStar className="text-amber-400" size={14} />
            <span className="text-sm font-medium text-slate-700 dark:text-slate-300">
              Favorites
            </span>
            <span className="text-xs text-slate-400 dark:text-slate-500">
              ({favoriteItems.length})
            </span>
          </div>
          {showFavorites ? (
            <FaChevronDown className="text-slate-400" size={12} />
          ) : (
            <FaChevronRight className="text-slate-400" size={12} />
          )}
        </button>
        
        {showFavorites && (
          <div className="px-2 pb-2">
            {favoriteItems.length === 0 ? (
              <p className="px-2 py-3 text-sm text-slate-400 dark:text-slate-500 text-center">
                No favorite items
              </p>
            ) : (
              favoriteItems.map(renderItem)
            )}
          </div>
        )}
      </div>

      {/* Footer hint */}
      <div className="px-4 py-2 bg-slate-50 dark:bg-slate-900/50 border-t border-slate-200 dark:border-slate-700">
        <p className="text-xs text-slate-400 dark:text-slate-500 text-center">
          Click an item to add it to the order
        </p>
      </div>
    </div>
  );
};

export default QuickAddRecent;
