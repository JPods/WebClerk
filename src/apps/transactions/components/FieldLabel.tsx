/**
 * FieldLabel - Consistent field label styling
 * - Mandatory fields: **bold**
 * - Locked fields: *italic*
 * - Mandatory + Locked: ***bold italic***
 */
import React from 'react';

interface FieldLabelProps {
  label: string;
  htmlFor?: string;
  mandatory?: boolean;
  locked?: boolean;
  className?: string;
}

const FieldLabel: React.FC<FieldLabelProps> = ({
  label,
  htmlFor,
  mandatory = false,
  locked = false,
  className = '',
}) => {
  const baseClass = 'block text-xs font-medium text-slate-600 dark:text-slate-400';
  const mandatoryClass = mandatory ? 'font-bold' : '';
  const lockedClass = locked ? 'italic' : '';
  
  return (
    <label
      htmlFor={htmlFor}
      className={`${baseClass} ${mandatoryClass} ${lockedClass} ${className}`.trim()}
    >
      {label}
      {mandatory && !locked && <span className="text-red-500 ml-0.5">*</span>}
    </label>
  );
};

export default FieldLabel;
