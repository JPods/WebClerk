/**
 * RecordLink — standard clickable record reference for wc3.
 * Click navigates to detail page. Shift-click opens in DataBrowser.
 *
 * Usage:
 *   <RecordLink model="customer" id={42} label="Acme Corp" />
 *   <RecordLink model="invoice" id={15} />  // shows ida or #15
 */
import React, { useCallback } from 'react';
import { useNavigate } from 'react-router-dom';

interface RecordLinkProps {
  model: string;
  id: number | string;
  label?: string;
  className?: string;
}

const MODEL_ROUTES: Record<string, string> = {
  customer: '/org/customer',
  vendor: '/org/vendor',
  employee: '/org/employee',
  rep: '/org/rep',
  manufacturer: '/org/manufacturer',
  order: '/transactions/order/detail',
  invoice: '/transactions/invoice/detail',
  proposal: '/transactions/proposal/detail',
  purchase: '/transactions/purchase/detail',
  workorder: '/transactions/workorder/detail',
  payment: '/transactions/payment/detail',
  item: '/products/item/detail',
  action: '/core/action/detail',
  contact: '/core/contact/detail',
};

export default function RecordLink({ model, id, label, className }: RecordLinkProps) {
  const navigate = useNavigate();

  const handleClick = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();

    if (e.shiftKey) {
      // Shift-click → databrowser
      navigate(`/${model}`);
      return;
    }

    const route = MODEL_ROUTES[model];
    if (route) {
      navigate(`${route}/${id}`);
    } else {
      navigate(`/${model}`);
    }
  }, [model, id, navigate]);

  return (
    <span onClick={handleClick}
      className={`text-blue-600 dark:text-blue-400 cursor-pointer hover:underline font-medium ${className || ''}`}
      title={`${model} #${id} · Shift-click for DataBrowser`}>
      {label || `#${id}`}
    </span>
  );
}
