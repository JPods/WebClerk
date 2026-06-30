/**
 * LoadingSpinner — standard loading indicator for wc3.
 * Three sizes: sm (inline), md (section), lg (full page).
 *
 * Usage:
 *   <LoadingSpinner />                    // medium, default
 *   <LoadingSpinner size="sm" />          // inline, next to text
 *   <LoadingSpinner size="lg" label="Loading records..." />  // full section
 */
import React from 'react';

interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  label?: string;
}

export default function LoadingSpinner({ size = 'md', label }: LoadingSpinnerProps) {
  const dim = size === 'sm' ? 16 : size === 'lg' ? 32 : 24;

  return (
    <div className={`flex items-center justify-center gap-2 ${size === 'lg' ? 'py-12' : size === 'sm' ? 'py-0' : 'py-4'}`}>
      <svg width={dim} height={dim} viewBox="0 0 24 24" fill="none" className="animate-spin">
        <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" strokeLinecap="round"
          className="text-gray-200 dark:text-gray-700" />
        <path d="M12 2a10 10 0 0 1 10 10" stroke="currentColor" strokeWidth="3" strokeLinecap="round"
          className="text-blue-600 dark:text-blue-400" />
      </svg>
      {label && <span className={`text-gray-500 dark:text-gray-400 ${size === 'sm' ? 'text-[10px]' : size === 'lg' ? 'text-sm' : 'text-xs'}`}>{label}</span>}
    </div>
  );
}
