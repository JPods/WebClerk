/**
 * SegaPartsPage — Custom page wrapper for the SEGA spare parts viewer.
 *
 * Registered as a custom page via Report record:
 *   purpose: 'custom-page'
 *   config.component: 'SegaPartsPage'
 *   config.route: '/custom/sega-parts'
 *
 * The page reads its SVG URL and mapping key from the Report config,
 * or uses defaults for JPods station parts.
 */
import React from 'react';
import SegaPartsViewer from '../components/SegaPartsViewer';

interface SegaPartsPageProps {
  config?: {
    svgUrl?: string;
    mappingKey?: string;
    title?: string;
  };
}

const SegaPartsPage: React.FC<SegaPartsPageProps> = ({ config }) => {
  const handleAddToCart = (item: any, qty: number) => {
    // For now, create an Action record (part request)
    // Future: integrate with ShoppingCart
    alert(`Added ${qty}x ${item.ida} — ${item.name} to cart`);
  };

  return (
    <div style={{ padding: 16 }}>
      <SegaPartsViewer
        svgUrl={config?.svgUrl || '/static/images/parts-diagram.svg'}
        mappingKey={config?.mappingKey || 'sega:jpods-station'}
        title={config?.title || 'JPods Station Parts'}
        onAddToCart={handleAddToCart}
      />
    </div>
  );
};

export default SegaPartsPage;
