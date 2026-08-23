/* LastChecked: 2026-07-31 | WhereUsed: SummaryCard, all transaction detail pages | WhoCreated: Unknown */
/**
 * FieldLabel - Consistent field label styling
 * - Shows exact field name (no prettifying)
 * - Hover shows full model.field path
 * - Shift+click opens field help
 * - Mandatory fields: **bold**
 * - Locked fields: *italic*
 */
import React from 'react';
import { openFieldHelp } from '@/components/common/HelpMenu';

interface FieldLabelProps {
  label: string;
  /** Model name for hover title and help lookup */
  model?: string;
  htmlFor?: string;
  mandatory?: boolean;
  locked?: boolean;
  className?: string;
}

const FieldLabel: React.FC<FieldLabelProps> = ({
  label,
  model = '',
  htmlFor,
  mandatory = false,
  locked = false,
  className = '',
}) => {
  const baseClass = 'block text-xs font-medium text-slate-600 dark:text-slate-400';
  const mandatoryClass = mandatory ? 'font-bold' : '';
  const lockedClass = locked ? 'italic' : '';
  const titleText = model ? `${model}.${label}` : label;

  const handleClick = (e: React.MouseEvent) => {
    if (e.shiftKey) {
      e.preventDefault();
      e.stopPropagation();
      openFieldHelp(model || 'system', label);
    }
  };

  return (
    <label
      htmlFor={htmlFor}
      title={titleText}
      onClick={handleClick}
      className={`${baseClass} ${mandatoryClass} ${lockedClass} ${className}`.trim()}
      style={{ cursor: 'default' }}
    >
      {label}
      {mandatory && !locked && <span className="text-red-500 ml-0.5">*</span>}
    </label>
  );
};

export default FieldLabel;
