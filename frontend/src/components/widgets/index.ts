/**
 * Widget Registry — the one map from a behavior type to the component that draws it.
 *
 * Every form reads it: the transaction form (FieldRow, HeaderRenderer), DynamicDetail,
 * the DataBrowser form (components/fields wraps each widget in BaseField for its label),
 * and print renderers (mode="print"). One widget per type (Bill, 2026-11-03: "a single widget").
 *
 * To add a widget:
 *   1. Create WidgetName.tsx implementing WidgetProps (take className; honor mode="print")
 *   2. Add it to WIDGETS below
 *   3. Use the type name in field behaviors and Report layouts
 */

export type { WidgetProps, WidgetOption, WidgetRegistryEntry } from "./types";

export { TextWidget } from "./TextWidget";
export { TextAreaWidget } from "./TextAreaWidget";
export { SelectWidget } from "./SelectWidget";
export { DtWidget, DtStamp, dtToLocal, localToDt } from "./DtWidget";
export { NumberWidget } from "./NumberWidget";
export { CurrencyWidget } from "./CurrencyWidget";
export { ReadonlyWidget } from "./ReadonlyWidget";
export { JsonTextWidget } from "./JsonTextWidget";
export { JsonWidget } from "./JsonWidget";
export { JsonEditor } from "./JsonEditor";
export { ContactLookup } from "./ContactLookup";
export { ContactSelectWidget } from "./ContactSelectWidget";
export { CheckboxWidget } from "./CheckboxWidget";
export { JsonTreeWidgetAdapter, JsonTree } from "./JsonTreeWidget";
export type { JsonTreeProps } from "./JsonTreeWidget";
export { EmailWidget } from "./EmailWidget";
export { PhoneWidget } from "./PhoneWidget";
export { UrlWidget, urlHref } from "./UrlWidget";
export { ZipWidget } from "./ZipWidget";
export { AddressWidget, addressHref } from "./AddressWidget";
export { GeoWidget, geoHref } from "./GeoWidget";
export { LookupWidget } from "./LookupWidget";

// Action widgets — buttons, toolbars, badges
export { WcButton } from "./WcButton";
export { WcBadge } from "./WcBadge";
export { WcToolbar } from "./WcToolbar";
export { WcIconButton } from "./WcIconButton";

// Time & Billing widgets
export { TimeClockWidget, TimeClockBadge } from "./TimeClockWidget";
export { BillableWidget } from "./BillableWidget";
export { OrgLookup } from "./OrgLookupWidget";

import type { WidgetProps } from "./types";
import { TextWidget } from "./TextWidget";
import { TextAreaWidget } from "./TextAreaWidget";
import { SelectWidget } from "./SelectWidget";
import { DtWidget, DtStamp } from "./DtWidget";
import { NumberWidget } from "./NumberWidget";
import { CurrencyWidget } from "./CurrencyWidget";
import { ReadonlyWidget } from "./ReadonlyWidget";
import { JsonTextWidget } from "./JsonTextWidget";
import { JsonWidget } from "./JsonWidget";
import { ContactLookup } from "./ContactLookup";
import { ContactSelectWidget } from "./ContactSelectWidget";
import { CheckboxWidget } from "./CheckboxWidget";
import { JsonTreeWidgetAdapter } from "./JsonTreeWidget";
import { TimeClockWidget } from "./TimeClockWidget";
import { BillableWidget } from "./BillableWidget";
import { EmailWidget } from "./EmailWidget";
import { PhoneWidget } from "./PhoneWidget";
import { UrlWidget } from "./UrlWidget";
import { ZipWidget } from "./ZipWidget";
import { AddressWidget } from "./AddressWidget";
import { GeoWidget } from "./GeoWidget";
import { LookupWidget } from "./LookupWidget";

/** A hidden field draws nothing. */
const HiddenWidget: React.FC<WidgetProps> = () => null;

/**
 * The registry. Keys are the behavior type names in a model's Setting and in Report layouts.
 */
export const WIDGETS: Record<string, React.ComponentType<WidgetProps>> = {
  text: TextWidget,
  textarea: TextAreaWidget,
  select: SelectWidget,
  date: DtWidget,          // a plan dt_ a person enters: local day and clock, stored UTC
  timestamp: DtStamp,      // a system dt_: shown local, never typed
  number: NumberWidget,
  currency: CurrencyWidget,
  readonly: ReadonlyWidget,
  masked: ReadonlyWidget,
  hidden: HiddenWidget,
  boolean: CheckboxWidget,
  checkbox: CheckboxWidget,
  email: EmailWidget,
  phone: PhoneWidget,
  url: UrlWidget,
  zip: ZipWidget,
  address: AddressWidget,
  geo: GeoWidget,
  lookup: LookupWidget,
  json: JsonWidget,
  "json-text": JsonTextWidget,
  "json-tree": JsonTreeWidgetAdapter,
  contact: ContactLookup,
  "contact-select": ContactSelectWidget,
  "time-clock": TimeClockWidget,
  billable: BillableWidget,
};

/**
 * Get a widget by type name. Falls back to TextWidget.
 */
export function getWidget(typeName: string): React.ComponentType<WidgetProps> {
  return WIDGETS[typeName] || TextWidget;
}
