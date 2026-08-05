/**
 * Widget Registry — maps type names to components.
 *
 * DynamicDetail, DataBrowser, and print renderers all use this.
 * One widget, two modes: screen (interactive) and print (static).
 *
 * To add a widget:
 *   1. Create WidgetName.tsx implementing WidgetProps
 *   2. Add it to WIDGETS below
 *   3. Use the type name in field configs and Report layouts
 */

export type { WidgetProps, WidgetOption, WidgetRegistryEntry } from "./types";

export { TextWidget } from "./TextWidget";
export { TextAreaWidget } from "./TextAreaWidget";
export { SelectWidget } from "./SelectWidget";
export { DateWidget } from "./DateWidget";
export { NumberWidget } from "./NumberWidget";
export { CurrencyWidget } from "./CurrencyWidget";
export { ReadonlyWidget } from "./ReadonlyWidget";
export { JsonTextWidget } from "./JsonTextWidget";
export { ContactLookup } from "./ContactLookup";
export { CheckboxWidget } from "./CheckboxWidget";
export { JsonTreeWidgetAdapter, JsonTree } from "./JsonTreeWidget";
export type { JsonTreeProps } from "./JsonTreeWidget";

// Action widgets — buttons, toolbars, badges
export { WcButton } from "./WcButton";
export { WcBadge } from "./WcBadge";
export { WcToolbar } from "./WcToolbar";
export { WcIconButton } from "./WcIconButton";

import type { WidgetProps } from "./types";
import { TextWidget } from "./TextWidget";
import { TextAreaWidget } from "./TextAreaWidget";
import { SelectWidget } from "./SelectWidget";
import { DateWidget } from "./DateWidget";
import { NumberWidget } from "./NumberWidget";
import { CurrencyWidget } from "./CurrencyWidget";
import { ReadonlyWidget } from "./ReadonlyWidget";
import { JsonTextWidget } from "./JsonTextWidget";
import { ContactLookup } from "./ContactLookup";
import { CheckboxWidget } from "./CheckboxWidget";
import { JsonTreeWidgetAdapter } from "./JsonTreeWidget";

/**
 * The registry. Keys are the type names used in field configs
 * and Report layout definitions.
 */
export const WIDGETS: Record<string, React.ComponentType<WidgetProps>> = {
  text: TextWidget,
  textarea: TextAreaWidget,
  select: SelectWidget,
  date: DateWidget,
  number: NumberWidget,
  currency: CurrencyWidget,
  readonly: ReadonlyWidget,
  "json-text": JsonTextWidget,
  "json-tree": JsonTreeWidgetAdapter,
  contact: ContactLookup,
  checkbox: CheckboxWidget,
};

/**
 * Get a widget by type name. Falls back to TextWidget.
 */
export function getWidget(typeName: string): React.ComponentType<WidgetProps> {
  return WIDGETS[typeName] || TextWidget;
}
