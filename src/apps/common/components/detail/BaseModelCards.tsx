/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
/**
 * BaseModelCards — Renders the standard Identity + Envelopes cards
 * that appear on every BaseModel-backed Detail page.
 *
 * Identity card: id, uuid, ida, dt_created, dt_modified, version,
 *   is_active, security_level, is_deleted, is_archived, health_rating
 *
 * Envelope cards (JSONB first-level keys):
 *   metadata, refs, prefs, comments
 *
 * Usage:
 *   <BaseModelCards data={record} />
 */
import React from "react";
import { Fingerprint, Layers } from "lucide-react";
import ScalarCard from "./ScalarCard";
import JsonCard from "./JsonCard";
import { FaCode } from "react-icons/fa";
import RawJsonCard from "./RawJsonCard";

export interface BaseModelCardsProps {
  /** The full record object */
  data: Record<string, unknown> | null | undefined;
  /** Show identity card (default: true) */
  showIdentity?: boolean;
  /** Show envelope cards (default: true) */
  showEnvelopes?: boolean;
  /** Default expanded state for these cards (default: false — collapsed) */
  defaultExpanded?: boolean;
}

function epochToDisplay(val: unknown): string {
  if (val === null || val === undefined || val === 0) return "—";
  if (typeof val === "number") {
    // epoch ms → human-readable
    try {
      const d = new Date(val > 1e12 ? val : val * 1000);
      return d.toLocaleString();
    } catch {
      return String(val);
    }
  }
  return String(val);
}

const BaseModelCards: React.FC<BaseModelCardsProps> = ({
  data,
  showIdentity = true,
  showEnvelopes = true,
  defaultExpanded = false,
}) => {
  if (!data) return null;

  //const data = { ...data, rawJson: data };
  //console.log("data2", data);
  return (
    <>
      {showIdentity && (
        <ScalarCard
          title="Identity"
          icon={<Fingerprint size={14} />}
          defaultExpanded={defaultExpanded}
          fields={[
            { label: "id", value: data.id },
            { label: "uuid", value: data.uuid },
            { label: "ida", value: data.ida },
            { label: "dt_created", value: epochToDisplay(data.dt_created) },
            { label: "dt_modified", value: epochToDisplay(data.dt_modified) },
            { label: "version", value: data.version },
            { label: "is_active", value: data.is_active },
            { label: "security_level", value: data.security_level },
            { label: "is_deleted", value: data.is_deleted },
            { label: "is_archived", value: data.is_archived },
            { label: "health_rating", value: data.health_rating },
          ]}
        />
      )}

      {showEnvelopes && (
        <>
          <JsonCard
            title="Metadata"
            icon={<Layers size={14} />}
            fieldName="metadata"
            data={data.metadata as Record<string, unknown> | null}
            defaultExpanded={defaultExpanded}
          />
          <JsonCard
            title="Refs"
            icon={<Layers size={14} />}
            fieldName="refs"
            data={data.refs as Record<string, unknown> | null}
            defaultExpanded={defaultExpanded}
          />
          <JsonCard
            title="Prefs"
            icon={<Layers size={14} />}
            fieldName="prefs"
            data={data.prefs as Record<string, unknown> | null}
            defaultExpanded={defaultExpanded}
          />
          {/* <JsonCard
            title="Comments"
            icon={<Layers size={14} />}
            fieldName="comments"
            data={data.comments as Record<string, unknown> | null}
            defaultExpanded={defaultExpanded}
          /> */}
          <RawJsonCard
            title="Raw"
            icon={<FaCode size={14} />}
            fieldName="rawJson"
            data={data as Record<string, unknown> | null}
            defaultExpanded={defaultExpanded}
          />
        </>
      )}
    </>
  );
};

export default BaseModelCards;
