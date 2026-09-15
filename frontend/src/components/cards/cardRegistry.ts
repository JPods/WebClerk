/**
 * Card Registry — maps component/footer names to React components.
 *
 * Cards are defined in layout.card as JSON specs. Most render as pure FieldRow
 * grids. Cards that need interactive behavior (customer search, autocomplete)
 * register a React component here by name.
 *
 * To add a new card component:
 *   1. Create the component (receives CardComponentProps)
 *   2. Register it here by name
 *   3. Reference the name in layout.card[name].component
 */
import React from 'react';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface CardFieldSpec {
  field: string;
  label?: string;
  type?: string;           // select, readonly, editable, search, action
  options?: string[];
  help?: string;
}

export interface CardSpec {
  title: string;
  title_ida?: string;      // field name for ID badge
  component?: string;      // registered component name
  footer?: string;         // registered footer component name
  source?: string;         // dot-path prefix for all fields
  fields: CardFieldSpec[];
}

export interface CardComponentProps {
  spec: CardSpec;
  data: any;
  isEditing: boolean;
  onChange: (field: string, value: unknown) => void;
  children?: React.ReactNode;  // default field rendering (passed by CardRenderer)
}

export interface FooterComponentProps {
  spec: CardSpec;
  data: any;
  isEditing: boolean;
  onChange: (field: string, value: unknown) => void;
}

// ---------------------------------------------------------------------------
// Registries
// ---------------------------------------------------------------------------

const CARD_COMPONENTS: Record<string, React.FC<CardComponentProps>> = {};
const FOOTER_COMPONENTS: Record<string, React.FC<FooterComponentProps>> = {};

/** Register a card component by name. */
export function registerCardComponent(name: string, component: React.FC<CardComponentProps>) {
  CARD_COMPONENTS[name] = component;
}

/** Register a footer component by name. */
export function registerFooterComponent(name: string, component: React.FC<FooterComponentProps>) {
  FOOTER_COMPONENTS[name] = component;
}

/** Look up a card component by name. Returns undefined if not registered. */
export function getCardComponent(name: string): React.FC<CardComponentProps> | undefined {
  return CARD_COMPONENTS[name];
}

/** Look up a footer component by name. Returns undefined if not registered. */
export function getFooterComponent(name: string): React.FC<FooterComponentProps> | undefined {
  return FOOTER_COMPONENTS[name];
}
