/* LastChecked: 2026-10-27 | WhereUsed: ItemDetail tabs | WhoCreated: Claude */
/**
 * ProductListPanel — generic list panel for product sub-models.
 * Reads records by parent item (usePanelRecords), renders with a card component; the panel
 * frame draws the header, count and status.
 * Used for: warehouse, variants, xrefs, specs, catalogs, usage.
 *
 * Usage:
 *   <ProductListPanel model="warehouse" itemId={256}
 *     CardComponent={WarehouseCard} headers={['Name','Bin','On Hand','Available']}
 *     headerWidths={['w-28','w-20','w-16','w-16']} />
 */
import React from 'react';
import { usePanelRecords } from '@/hooks/usePanelRecords';
import { usePanelFrame, PanelLabels } from '@/apps/common/components/CollapsiblePanel';

export interface ProductListPanelProps {
  model: string;
  itemId: number;
  filterField?: string;  // default: 'item_id'
  CardComponent: React.FC<any>;
  headers: string[];
  headerWidths?: string[];
  onCardClick?: (id: number) => void;
}

const ProductListPanel: React.FC<ProductListPanelProps> = ({
  model, itemId, filterField = 'item_id',
  CardComponent, headers, headerWidths, onCardClick,
}) => {
  const { records, status } = usePanelRecords(model, { [filterField]: itemId, limit: 200 },
    { emptyText: `No ${model} records` });
  usePanelFrame({ badge: records.length, status });

  return (
    <div className="p-2">
      {records.length > 0 && (
        <PanelLabels>
          {headers.map((h, i) => (
            <span key={h} className={headerWidths?.[i] || 'flex-1'}>{h}</span>
          ))}
        </PanelLabels>
      )}
      {records.map((r: any) => (
        <CardComponent key={r.id} data={r} onClick={onCardClick} />
      ))}
    </div>
  );
};

export default ProductListPanel;
