/**
 * TimeClockCard — db.card for action.config.times
 *
 * Shows clock in/out entries with live timer. Self-registers as 'time_clock'.
 * Delegates rendering to TimeClockWidget (same visuals, card vs widget contract).
 *
 * Setting layout reference:
 *   cardSpecs.time_clock = { title: "times", component: "time_clock", source: "config", fields: [] }
 */
import React, { useCallback, useMemo } from 'react';
import { registerCardComponent } from './cardRegistry';
import type { CardComponentProps } from './cardRegistry';
import { TimeClockWidget } from '../widgets/TimeClockWidget';
import { saveRecord } from '@/api/wcapi';

const TimeClockCard: React.FC<CardComponentProps> = ({ data, isEditing, onChange }) => {
  const times = useMemo(() => data?.config?.times ?? { entries: [] }, [data?.config?.times]);

  const handleChange = useCallback(
    (updatedTimes: any) => {
      // Update config.times on the record
      onChange('config.times', updatedTimes);

      // Persist immediately — clock in/out should not wait for form save
      if (data?.id) {
        const config = { ...(data.config || {}), times: updatedTimes };
        saveRecord('action', { id: data.id, config }).catch(() => {});
      }
    },
    [data?.id, data?.config, onChange]
  );

  return (
    <TimeClockWidget
      name="config.times"
      value={times}
      onChange={handleChange}
      disabled={!isEditing}
      record={data}
    />
  );
};

registerCardComponent('time_clock', TimeClockCard);

export default TimeClockCard;
