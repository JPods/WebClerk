/**
 * SegaPartsViewer — Interactive SVG spare parts diagram.
 *
 * Displays an SVG exploded diagram where each part region is clickable.
 * Clicking a part fetches the item details from WCAPI and shows them
 * in a slide panel with price, availability, and add-to-cart.
 *
 * SVG regions must have data-item-id="<item.ida>" or data-part="<partNumber>".
 * A mapping JSON (from a Setting record or props) maps region IDs to item IDs.
 *
 * Usage:
 *   <SegaPartsViewer
 *     svgUrl="/static/images/jpods-station-exploded.svg"
 *     mappingKey="sega:jpods-station"
 *   />
 *
 * The SEGA pattern: customer sees a picture of what they have, clicks what they need.
 */
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { getRecords } from '../../api/wcapi';
import { formatCurrency } from '@/utils/stringUtils';

interface PartMapping {
  /** SVG element ID or data-part value */
  regionId: string;
  /** Item ida (SKU) in the database */
  itemIda: string;
  /** Human-readable label shown on hover */
  label?: string;
}

interface ItemDetail {
  id: number;
  ida: string;
  name: string;
  description?: string;
  sku?: string;
  sell?: { price?: number };
  quantity?: { available?: number; on_hand?: number };
  images?: string[];
  [key: string]: any;
}

interface SegaPartsViewerProps {
  /** URL to SVG file, or inline SVG string */
  svgUrl?: string;
  svgContent?: string;
  /** Part mappings — array of regionId -> itemIda */
  mappings?: PartMapping[];
  /** Setting key to load mappings from (e.g., "sega:jpods-station") */
  mappingKey?: string;
  /** Title shown above the diagram */
  title?: string;
  /** Callback when user adds item to cart */
  onAddToCart?: (item: ItemDetail, qty: number) => void;
}

const fmt = (n?: number) => formatCurrency(n);

const SegaPartsViewer: React.FC<SegaPartsViewerProps> = ({
  svgUrl,
  svgContent,
  mappings: propMappings,
  mappingKey,
  title = 'Spare Parts',
  onAddToCart,
}) => {
  const svgContainerRef = useRef<HTMLDivElement>(null);
  const [mappings, setMappings] = useState<PartMapping[]>(propMappings || []);
  const [selectedItem, setSelectedItem] = useState<ItemDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [qty, setQty] = useState(1);
  const [hoveredPart, setHoveredPart] = useState<string | null>(null);
  const [svgLoaded, setSvgLoaded] = useState(false);

  // Load mappings from Setting if mappingKey provided
  useEffect(() => {
    if (mappingKey && !propMappings) {
      getRecords('setting', { name: mappingKey, limit: 1 }).then(res => {
        const setting = res?.results?.[0];
        if (setting?.config?.mappings) {
          setMappings(setting.config.mappings);
        }
      });
    }
  }, [mappingKey, propMappings]);

  // Load SVG from URL
  useEffect(() => {
    if (svgUrl && svgContainerRef.current) {
      fetch(svgUrl)
        .then(r => r.text())
        .then(text => {
          if (svgContainerRef.current) {
            svgContainerRef.current.innerHTML = text;
            setSvgLoaded(true);
          }
        });
    } else if (svgContent && svgContainerRef.current) {
      svgContainerRef.current.innerHTML = svgContent;
      setSvgLoaded(true);
    }
  }, [svgUrl, svgContent]);

  // Attach click/hover handlers to SVG regions
  useEffect(() => {
    if (!svgLoaded || !svgContainerRef.current) return;
    const container = svgContainerRef.current;

    // Find all elements with data-part or data-item-id
    const parts = container.querySelectorAll('[data-part], [data-item-id]');
    parts.forEach(el => {
      (el as HTMLElement).style.cursor = 'pointer';
      el.classList.add('sega-part');
    });

    // Also highlight mapped regions by ID
    mappings.forEach(m => {
      const el = container.querySelector(`#${CSS.escape(m.regionId)}`) ||
                 container.querySelector(`[data-part="${m.regionId}"]`);
      if (el) {
        (el as HTMLElement).style.cursor = 'pointer';
        el.classList.add('sega-part');
        el.setAttribute('data-item-id', m.itemIda);
        if (m.label) el.setAttribute('title', m.label);
      }
    });
  }, [svgLoaded, mappings]);

  // Handle clicks on SVG
  const handleSvgClick = useCallback((e: React.MouseEvent) => {
    const target = (e.target as HTMLElement).closest('[data-item-id], [data-part]');
    if (!target) return;

    const itemIda = target.getAttribute('data-item-id') ||
                    mappings.find(m => m.regionId === target.id)?.itemIda ||
                    mappings.find(m => m.regionId === target.getAttribute('data-part'))?.itemIda;

    if (!itemIda) return;

    setLoading(true);
    setQty(1);
    getRecords('item', { ida: itemIda, limit: 1 })
      .then(res => {
        const item = res?.results?.[0];
        if (item) setSelectedItem(item);
      })
      .finally(() => setLoading(false));
  }, [mappings]);

  // Handle hover
  const handleSvgHover = useCallback((e: React.MouseEvent) => {
    const target = (e.target as HTMLElement).closest('.sega-part');
    setHoveredPart(target?.getAttribute('data-item-id') || target?.id || null);
  }, []);

  return (
    <div className="wc-sega-viewer">
      <h2 className="wc-sega-title">{title}</h2>

      <div className="wc-sega-layout">
        {/* SVG diagram */}
        <div
          className="wc-sega-diagram"
          ref={svgContainerRef}
          onClick={handleSvgClick}
          onMouseMove={handleSvgHover}
          onMouseLeave={() => setHoveredPart(null)}
        />

        {/* Part detail panel */}
        <div className={`wc-sega-panel ${selectedItem ? 'wc-sega-panel--open' : ''}`}>
          {loading && <div className="wc-sega-loading">Loading part details...</div>}

          {selectedItem && !loading && (
            <div className="wc-sega-detail">
              <button
                className="wc-sega-close"
                onClick={() => setSelectedItem(null)}
              >
                &times;
              </button>
              <h3 className="wc-sega-part-name">{selectedItem.name}</h3>
              <div className="wc-sega-part-sku">Part # {selectedItem.ida}</div>
              {selectedItem.description && (
                <p className="wc-sega-part-desc">{selectedItem.description}</p>
              )}
              <div className="wc-sega-part-price">{fmt(selectedItem.sell?.price)}</div>
              <div className="wc-sega-part-avail">
                {(selectedItem.quantity?.available ?? 0) > 0
                  ? `${selectedItem.quantity?.available} available`
                  : 'Contact for availability'}
              </div>
              <div className="wc-sega-order">
                <label>
                  Qty:
                  <input
                    type="number"
                    min={1}
                    value={qty}
                    onChange={e => setQty(Math.max(1, parseInt(e.target.value) || 1))}
                    className="wc-sega-qty-input"
                  />
                </label>
                <button
                  className="wc-sega-add-btn"
                  onClick={() => onAddToCart?.(selectedItem, qty)}
                >
                  Add to Cart
                </button>
              </div>
            </div>
          )}

          {!selectedItem && !loading && (
            <div className="wc-sega-placeholder">
              Click a part on the diagram to see details
            </div>
          )}
        </div>
      </div>

      {hoveredPart && (
        <div className="wc-sega-hover-label">{hoveredPart}</div>
      )}
    </div>
  );
};

export default SegaPartsViewer;
