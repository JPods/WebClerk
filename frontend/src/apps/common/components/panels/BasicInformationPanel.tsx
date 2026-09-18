/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
/**
 * BasicInformationPanel - Compact read-only display of org basic information
 *
 * Displays common OrgBase scalar fields in a horizontal layout.
 * Reusable across all org apps (customer, vendor, employee, rep, manufacturer).
 */
import React from "react";
import { FaBuilding } from "react-icons/fa";
import { withDevIdentifier } from "@/components/common/DevIdentifier";
import { defaultCountries, usePhoneInput } from "react-international-phone";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface BasicInformationData {
  id?: number;
  display_name?: string;
  attention?: string | null;
  email?: string | null;
  phone?: string | null;
  price_level?: string | null;
  terms?: string | null;
  terms_id?: number | null;
  address_full?: string | null;
  contact_id?: number | null;
  status?: string;
  org_type?: string;
  version?: number;
  is_active?: boolean;
}

interface BasicInformationPanelProps {
  /** Organization data */
  data: BasicInformationData;
  /** Number of columns (2 or 3) */
  columns?: 2 | 3;
  /** Show header with icon */
  showHeader?: boolean;
  /** Custom title */
  title?: string;
  /** Additional CSS classes */
  className?: string;
}

// ---------------------------------------------------------------------------
// Row Component - Horizontal label/value pair
// ---------------------------------------------------------------------------

interface RowProps {
  label: string;
  value: React.ReactNode;
  className?: string;
}

const Row: React.FC<RowProps> = ({ label, value, className = "" }) => (
  <div className={`flex items-center gap-2 ${className}`}>
    <dt className="w-25 shrink text-left text-sm" style={{ color: 'var(--db-text-muted)' }}>
      {label} :
    </dt>
    <dd className="font-medium text-sm" style={{ color: 'var(--db-text)' }}>
      {value || "—"}
    </dd>
  </div>
);

// ---------------------------------------------------------------------------
// Status Badge Component
// ---------------------------------------------------------------------------

const ActiveBadge: React.FC<{ isActive: boolean }> = ({ isActive }) => (
  <span
    className="inline-flex items-center px-2 py-0.5 text-xs font-medium rounded-full"
    style={{
      background: 'var(--db-surface-alt)',
      color: isActive ? 'var(--db-text)' : 'var(--db-text-dim)',
    }}
  >
    {isActive ? "Yes" : "No"}
  </span>
);
/**
 * PhoneDisplay - Format and display phone numbers using react-international-phone
 * Uses the library's formatting logic for consistent display with the input component
 */
const PhoneDisplay: React.FC<{ value?: string | null }> = ({ value }) => {
  const { inputValue } = usePhoneInput({
    value: value || "",
    countries: defaultCountries,
    defaultCountry: "us",
    forceDialCode: true,
  });

  if (!value) return null;
  return <>{inputValue}</>;
};

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

const BasicInformationPanel: React.FC<BasicInformationPanelProps> = ({
  data,
  columns = 3,
  showHeader = true,
  title = "Basic Information",
  className = "",
}) => {
  const gridCols = columns === 3 ? "lg:grid-cols-3" : "lg:grid-cols-2";

  return (
    <div
      className={`rounded-lg p-2 ${className}`}
      style={{ background: 'var(--db-surface-alt)' }}
    >
      {showHeader && (
        <h3 className="text-sm font-semibold mb-3 flex items-center gap-2" style={{ color: 'var(--db-text)' }}>
          <FaBuilding size={16} />
          {title}
        </h3>
      )}
      <dl className={`grid grid-cols-1 ${gridCols} gap-x-6 gap-y-2 text-sm`}>
        <Row label="display_name" value={data.display_name} />
        <Row
          label="org_type"
          value={
            data.org_type ? (
              <span className="capitalize">{data.org_type}</span>
            ) : null
          }
        />
        <Row label="terms" value={data.terms} />
        <Row label="attention" value={data.attention} />
        <Row label="phone" value={<PhoneDisplay value={data.phone} />} />
        <Row label="email" value={data.email} />
      </dl>
      <dl
        className={`grid grid-cols-1 ${gridCols} gap-x-6 gap-y-2 text-sm py-2`}
      >
        <Row label="address_full" value={data.address_full} className="w-100" />
      </dl>
      <dl
        className={`grid grid-cols-1 ${gridCols} gap-x-6 gap-y-2 text-sm pb-2`}
      >
        <Row label="price_level" value={data.price_level} />

        {/* <Row label="terms_id" value={data.terms_id?.toString()} /> */}

        {/* <Row label="contact_id" value={data.contact_id?.toString()} /> */}

        <Row
          label="status"
          value={
            data.status ? (
              <span className="capitalize">{data.status}</span>
            ) : null
          }
        />
        <Row label="version" value={data.version?.toString()} />
        <Row
          label="is_active"
          value={<ActiveBadge isActive={data.is_active ?? false} />}
        />
      </dl>
    </div>
  );
};

export default withDevIdentifier(
  BasicInformationPanel,
  "BasicInformationPanel",
  "teal",
  'apps/common/components/panels/BasicInformationPanel.tsx',
);
