/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
/**
 * PageHeader - Displays page title with optional breadcrumb navigation
 */
import React from 'react';
import { Link } from 'react-router-dom';

interface Breadcrumb {
  label: string;
  href?: string;
}

interface PageHeaderProps {
  /** Page title */
  title: string;
  /** Optional breadcrumb trail */
  breadcrumbs?: Breadcrumb[];
  /** Optional subtitle/description */
  subtitle?: string;
  /** Additional CSS classes */
  className?: string;
}

export const PageHeader: React.FC<PageHeaderProps> = ({
  title,
  breadcrumbs,
  subtitle,
  className = '',
}) => {
  return (
    <div className={`flex flex-col ${className}`}>
      {/* Breadcrumbs */}
      {breadcrumbs && breadcrumbs.length > 0 && (
        <nav className="flex items-center text-sm text-slate-500 dark:text-slate-400 mb-1">
          {breadcrumbs.map((crumb, index) => (
            <React.Fragment key={index}>
              {index > 0 && (
                <span className="mx-2 text-slate-300 dark:text-slate-600">/</span>
              )}
              {crumb.href ? (
                <Link
                  to={crumb.href}
                  className="hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
                >
                  {crumb.label}
                </Link>
              ) : (
                <span className="text-slate-700 dark:text-slate-300 font-medium">
                  {crumb.label}
                </span>
              )}
            </React.Fragment>
          ))}
        </nav>
      )}
      
      {/* Title */}
      <h1 className="text-xl font-semibold text-slate-900 dark:text-white">
        {title}
      </h1>
      
      {/* Subtitle */}
      {subtitle && (
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
          {subtitle}
        </p>
      )}
    </div>
  );
};

export default PageHeader;
