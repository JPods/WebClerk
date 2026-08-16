/**
 * Card system — import this to ensure all card components are registered.
 *
 * New card components self-register via registerCardComponent/registerFooterComponent
 * on import. Add new imports here to include them in the registry.
 */
export { default as CardRenderer } from './CardRenderer';
export type { CardSpec, CardFieldSpec, CardComponentProps, FooterComponentProps } from './cardRegistry';
export { getCardComponent, getFooterComponent, registerCardComponent, registerFooterComponent } from './cardRegistry';

// Self-registering components — import triggers registration
import './CustomerSearchCard';
import './ActionSummaryFooter';
