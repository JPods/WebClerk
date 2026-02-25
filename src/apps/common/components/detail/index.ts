/**
 * Shared Detail card components — barrel export
 *
 * Reusable building blocks for model Detail pages:
 * - InfoRow: single label/value row
 * - ScalarCard: collapsible card of scalar fields
 * - JsonCard: collapsible card showing JSONB first-level keys
 * - BaseModelCards: standard Identity + Envelopes cards for BaseModel records
 */

export { default as InfoRow, formatDisplayValue } from "./InfoRow";
export type { InfoRowProps } from "./InfoRow";

export { default as ScalarCard } from "./ScalarCard";
export type { ScalarCardProps, ScalarField } from "./ScalarCard";

export { default as JsonCard } from "./JsonCard";
export type { JsonCardProps } from "./JsonCard";

export { default as BaseModelCards } from "./BaseModelCards";
export type { BaseModelCardsProps } from "./BaseModelCards";
