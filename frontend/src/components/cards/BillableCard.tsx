/**
 * BillableCard — db.card for action.config.billable
 *
 * Shows billing configuration: bill-to, rate, estimates vs actuals,
 * Alice learning signal. Self-registers as 'billable'.
 *
 * Setting layout reference:
 *   cardSpecs.billable = { title: "billing", component: "billable", source: "config", fields: [] }
 */
import React, { useCallback, useMemo } from 'react';
import { registerCardComponent } from './cardRegistry';
import type { CardComponentProps } from './cardRegistry';
import { BillableWidget } from '../widgets/BillableWidget';

const BillableCard: React.FC<CardComponentProps> = ({ data, isEditing, onChange }) => {
  const billable = useMemo(
    () => data?.config?.billable ?? { is_billable: true, rate_unit: 'hour', currency: 'USD' },
    [data?.config?.billable]
  );

  const handleChange = useCallback(
    (updatedBillable: any) => {
      onChange('config.billable', updatedBillable);
    },
    [onChange]
  );

  return (
    <BillableWidget
      name="config.billable"
      value={billable}
      onChange={handleChange}
      disabled={!isEditing}
      record={data}
    />
  );
};

registerCardComponent('billable', BillableCard);

export default BillableCard;
