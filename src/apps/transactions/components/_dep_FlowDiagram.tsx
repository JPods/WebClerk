/**
 * FlowDiagram - Visual lineage showing source → current → children relationships
 * Displays transaction hierarchy and audit trail
 */
import React from 'react';
import { 
  FaArrowRight, 
  FaFileInvoice, 
  FaShoppingCart, 
  FaClipboardList,
  FaTruck,
  FaBoxOpen,
  FaFileAlt,
  FaLink,
  FaExternalLinkAlt
} from 'react-icons/fa';
import type { TransactionFlow, TransactionSource } from '../types/transactionTypes';

interface FlowDiagramProps {
  flow?: TransactionFlow;
  source?: TransactionSource;
  currentId?: number;
  currentType?: string;
  currentNumber?: string;
}

type TransactionType = 'order' | 'invoice' | 'pick' | 'ship' | 'receive' | 'quote' | 'po' | 'credit' | string;

const getTransactionIcon = (type: TransactionType): React.ReactNode => {
  const iconProps = { size: 16 };
  switch (type.toLowerCase()) {
    case 'order':
    case 'sales_order':
      return <FaShoppingCart {...iconProps} />;
    case 'invoice':
    case 'sales_invoice':
      return <FaFileInvoice {...iconProps} />;
    case 'quote':
    case 'sales_quote':
      return <FaClipboardList {...iconProps} />;
    case 'pick':
    case 'pick_ticket':
      return <FaBoxOpen {...iconProps} />;
    case 'ship':
    case 'shipment':
      return <FaTruck {...iconProps} />;
    case 'po':
    case 'purchase_order':
      return <FaClipboardList {...iconProps} />;
    default:
      return <FaFileAlt {...iconProps} />;
  }
};

const getTypeLabel = (type: TransactionType): string => {
  const labels: Record<string, string> = {
    'order': 'Order',
    'sales_order': 'Sales Order',
    'invoice': 'Invoice',
    'sales_invoice': 'Sales Invoice',
    'quote': 'Quote',
    'sales_quote': 'Sales Quote',
    'pick': 'Pick Ticket',
    'pick_ticket': 'Pick Ticket',
    'ship': 'Shipment',
    'shipment': 'Shipment',
    'receive': 'Receive',
    'po': 'Purchase Order',
    'purchase_order': 'Purchase Order',
    'credit': 'Credit Note',
    'credit_note': 'Credit Note',
  };
  return labels[type.toLowerCase()] ?? type;
};

const TransactionNode: React.FC<{
  type: string;
  number?: string;
  id?: number;
  date?: string;
  status?: string;
  isCurrent?: boolean;
  onClick?: () => void;
}> = ({ type, number, id, date, status, isCurrent, onClick }) => (
  <div
    onClick={onClick}
    className={`
      relative flex flex-col items-center p-4 rounded-lg border-2 transition-all cursor-pointer
      ${isCurrent 
        ? 'bg-blue-50 dark:bg-blue-900/30 border-blue-500' 
        : 'bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 hover:border-blue-300 dark:hover:border-blue-600'
      }
      min-w-[140px]
    `}
  >
    {isCurrent && (
      <span className="absolute -top-2 -right-2 px-2 py-0.5 text-xs bg-blue-500 text-white rounded-full">
        Current
      </span>
    )}
    <div className={`mb-2 ${isCurrent ? 'text-blue-600 dark:text-blue-400' : 'text-slate-500 dark:text-slate-400'}`}>
      {getTransactionIcon(type)}
    </div>
    <span className="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide">
      {getTypeLabel(type)}
    </span>
    {number && (
      <span className={`text-sm font-bold ${isCurrent ? 'text-blue-700 dark:text-blue-300' : 'text-slate-900 dark:text-white'}`}>
        {number}
      </span>
    )}
    {date && (
      <span className="text-xs text-slate-400 mt-1">
        {new Date(date).toLocaleDateString()}
      </span>
    )}
    {status && (
      <span className={`
        text-xs px-2 py-0.5 rounded-full mt-2
        ${status === 'completed' || status === 'posted' ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' :
          status === 'pending' || status === 'draft' ? 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400' :
          status === 'cancelled' ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400' :
          'bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300'}
      `}>
        {status}
      </span>
    )}
    {!isCurrent && onClick && (
      <FaExternalLinkAlt size={10} className="absolute top-2 right-2 text-slate-300 dark:text-slate-600" />
    )}
  </div>
);

const Arrow: React.FC<{ label?: string }> = ({ label }) => (
  <div className="flex flex-col items-center justify-center px-2">
    <FaArrowRight className="text-slate-300 dark:text-slate-600" size={20} />
    {label && (
      <span className="text-xs text-slate-400 mt-1">{label}</span>
    )}
  </div>
);

const FlowDiagram: React.FC<FlowDiagramProps> = ({
  flow = {},
  source = {},
  currentId,
  currentType = 'transaction',
  currentNumber,
}) => {
  // Build chain of parents (from oldest to current)
  const parentChain = flow.parent_chain ?? [];
  
  // Children
  const children = flow.children ?? [];
  
  // Source info (external source like webstore, EDI, etc.)
  const hasExternalSource = source.origin || source.channel;

  const handleNodeClick = (type: string, id?: number) => {
    if (!id || id === currentId) return;
    // Navigate to the transaction - in real implementation this would use router
    console.log(`Navigate to ${type} #${id}`);
  };

  return (
    <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-4">
      {/* Header */}
      <div className="flex items-center gap-2 mb-4 pb-2 border-b border-slate-200 dark:border-slate-700">
        <FaLink className="text-slate-400" size={14} />
        <h3 className="font-semibold text-slate-900 dark:text-white">Transaction Flow</h3>
        <span className="text-xs text-slate-400 ml-auto">Document lineage & audit trail</span>
      </div>

      {/* External Source Info */}
      {hasExternalSource && (
        <div className="mb-4 p-3 bg-slate-50 dark:bg-slate-900/50 rounded-lg text-sm">
          <span className="text-slate-500 dark:text-slate-400">Origin: </span>
          <span className="font-medium text-slate-700 dark:text-slate-300">
            {source.origin ?? 'Unknown'}
          </span>
          {source.channel && (
            <>
              <span className="text-slate-500 dark:text-slate-400 mx-2">via</span>
              <span className="font-medium text-slate-700 dark:text-slate-300">{source.channel}</span>
            </>
          )}
          {source.external_id && (
            <>
              <span className="text-slate-500 dark:text-slate-400 mx-2">•</span>
              <span className="font-mono text-xs text-slate-600 dark:text-slate-400">
                Ext ID: {source.external_id}
              </span>
            </>
          )}
        </div>
      )}

      {/* Flow Diagram */}
      <div className="overflow-x-auto">
        <div className="flex items-center justify-start gap-1 min-w-max py-4">
          {/* Parent Chain */}
          {parentChain.map((parent, idx) => (
            <React.Fragment key={`parent-${idx}`}>
              <TransactionNode
                type={parent.type ?? 'transaction'}
                number={parent.number}
                id={parent.id}
                date={parent.date}
                status={parent.status}
                onClick={() => handleNodeClick(parent.type ?? 'transaction', parent.id)}
              />
              <Arrow />
            </React.Fragment>
          ))}

          {/* Current Transaction */}
          <TransactionNode
            type={currentType}
            number={currentNumber}
            id={currentId}
            isCurrent
          />

          {/* Children */}
          {children.length > 0 && (
            <>
              <Arrow />
              <div className="flex flex-col gap-2">
                {children.map((child, idx) => (
                  <TransactionNode
                    key={`child-${idx}`}
                    type={child.type ?? 'transaction'}
                    number={child.number}
                    id={child.id}
                    date={child.date}
                    status={child.status}
                    onClick={() => handleNodeClick(child.type ?? 'transaction', child.id)}
                  />
                ))}
              </div>
            </>
          )}
        </div>
      </div>

      {/* Flow Metadata */}
      {(flow.created_from || flow.copied_from) && (
        <div className="mt-4 pt-4 border-t border-slate-200 dark:border-slate-700 text-xs text-slate-500 dark:text-slate-400">
          {flow.created_from && (
            <div>
              <span className="font-medium">Created from: </span>
              {flow.created_from.type} #{flow.created_from.number ?? flow.created_from.id}
            </div>
          )}
          {flow.copied_from && (
            <div>
              <span className="font-medium">Copied from: </span>
              {flow.copied_from.type} #{flow.copied_from.number ?? flow.copied_from.id}
            </div>
          )}
        </div>
      )}

      {/* Empty State */}
      {!parentChain.length && !children.length && !hasExternalSource && (
        <div className="text-center py-8 text-slate-400">
          <FaFileAlt size={24} className="mx-auto mb-2 opacity-50" />
          <p className="text-sm">This is a standalone document with no linked transactions</p>
        </div>
      )}
    </div>
  );
};

export default FlowDiagram;
