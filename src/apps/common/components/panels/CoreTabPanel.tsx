/**
 * CoreTabPanel
 *
 * Reusable tabbed detail panel for all org model pages
 * (CustomerDetail, VendorDetail, ManufacturerDetail, RepDetail, etc.).
 *
 * Encapsulates the standard tab bar + panel content for:
 *   actions · comments · contacts · documents · qa · raw
 *
 * The caller provides entity-specific save/refresh callbacks; all
 * internal dispatch (toasts) is handled here.
 */
import React from "react";
import { useDispatch } from "react-redux";
import { showToast } from "@/store/slices/toastSlice";
import {
  CommentsPanel,
  ActionsPanel,
  DocumentsPanel,
  RawDataPanel,
  ContactPanel,
  QAPanel,
} from "@/apps/common/components/panels";
import type { RefContact } from "@/apps/common/components/panels";
import { DetailTabs } from "@/components/common/DetailTabs";
import type { TabConfig } from "@/components/common/DetailTabs";

// Re-use DetailTabs' standard-tab union to stay type-safe
type StandardTabKey =
  | "actions"
  | "comments"
  | "contacts"
  | "documents"
  | "financials"
  | "overview"
  | "raw";

export interface CoreTabPanelProps {
  // ── Tab bar ──────────────────────────────────────────────
  entityType: string;
  activeTab: string;
  onTabChange: (tab: string) => void;
  standardTabs?: StandardTabKey[];
  additionalTabs?: TabConfig[];
  tabBadges?: Record<string, number>;
  columnCount: number;
  onColumnCountChange: (count: number) => void;
  showColumnSelector?: boolean;

  // ── Record data ──────────────────────────────────────────
  data: any;
  entityId: number;

  // ── Edit state ───────────────────────────────────────────
  mode: "view" | "edit" | "add";
  isEditing: boolean;

  // ── Save callbacks (entity-specific, supplied by parent) ─
  /** Called with the updated comments object — should call the entity update API */
  onSaveComments: (comments: any) => Promise<void>;
  /** Called with the updated actions object — should call the entity update API */
  onSaveActions: (actions: any) => Promise<void>;
  /** Re-fetches the record from the server and updates local state */
  onRefreshRecord: () => Promise<void>;
  /** Shallow-merges a patch into the local record state (optimistic update) */
  onRecordChange: (patch: Record<string, any>) => void;

  // ── Contact panel ────────────────────────────────────────
  fkContacts: RefContact[];
  fkContactsLoading?: boolean;
  orgDisplayName?: string;
  primaryContactId?: number | null;
  onSetPrimary?: (contact: RefContact) => void;
  onRefreshContacts?: () => void;
  onContactsChange?: (contacts: RefContact[]) => void;
  onContactSaveSuccess?: () => void;
  /** Pass entity id as customer_id when the org IS a customer (pre-links new contacts) */
  customer_id?: number;

  // ── Action panel options ─────────────────────────────────
  contactOptions?: Array<{ id: string; label: string }>;
  projectOptions?: Array<{ id: string; name?: string; intent?: string }>;

  // ── User ─────────────────────────────────────────────────
  currentUser?: { name_first?: string; name_last?: string; id?: number };

  /**
   * Additional tab content beyond the standard set.
   * Render conditionally based on activeTab in the caller:
  *   extraTabContent={<>{activeTab === "financial" && <TransactionTabPanel ... />}</>}
   */
  extraTabContent?: React.ReactNode;
}

export default function CoreTabPanel({
  entityType,
  activeTab,
  onTabChange,
  standardTabs = ["actions", "comments", "documents", "raw"],
  additionalTabs = [],
  tabBadges = {},
  columnCount,
  onColumnCountChange,
  showColumnSelector = false,
  data,
  entityId,
  mode,
  isEditing,
  onSaveComments,
  onSaveActions,
  onRefreshRecord,
  onRecordChange,
  fkContacts,
  fkContactsLoading,
  orgDisplayName,
  primaryContactId,
  onSetPrimary,
  onRefreshContacts,
  onContactsChange,
  onContactSaveSuccess,
  customer_id,
  contactOptions = [],
  projectOptions = [],
  currentUser,
  extraTabContent,
}: CoreTabPanelProps) {
  const dispatch = useDispatch();

  return (
    <div>
      <DetailTabs
        entityType={entityType}
        activeTab={activeTab}
        onTabChange={onTabChange}
        standardTabs={standardTabs}
        additionalTabs={additionalTabs}
        badges={tabBadges}
        showColumnSelector={showColumnSelector}
        columnCount={columnCount as 2 | 3}
        onColumnCountChange={onColumnCountChange as (count: 2 | 3) => void}
      />

      <div className="flex-1 cus-bg-black-light rounded-md">
        <div className="p-2">
          {activeTab === "comments" && (
            <CommentsPanel
              entityType={entityType}
              entityId={entityId}
              comments={data?.comments}
              isEditing={mode !== "view" || isEditing}
              onChange={(comments) => onRecordChange({ comments })}
              onSave={async (comments) => {
                try {
                  await onSaveComments(comments);
                  dispatch(
                    showToast({ message: "Comments saved", type: "success" }),
                  );
                } catch {
                  dispatch(
                    showToast({
                      message: "Failed to save comments",
                      type: "error",
                    }),
                  );
                }
              }}
              currentUser={
                `${currentUser?.name_first ?? ""} ${currentUser?.name_last ?? ""}`.trim() ||
                undefined
              }
              currentUserId={currentUser?.id}
            />
          )}

          {activeTab === "actions" && (
            <ActionsPanel
              entityType={entityType}
              entityId={entityId}
              data={Array.isArray(data?.actions) ? data.actions : undefined}
              actionIds={
                data?.actions &&
                typeof data.actions === "object" &&
                "ids" in data.actions
                  ? (data.actions as { ids?: number[] }).ids
                  : undefined
              }
              viewMode="table"
              isEditing={isEditing}
              parentModelName={entityType}
              parentIdOverride={entityId || undefined}
              onChange={(actions) => onRecordChange({ actions })}
              onActionIdsChange={(ids) =>
                onRecordChange({ actions: { ids } })
              }
              onSave={async (actions) => {
                try {
                  await onSaveActions(actions);
                  try {
                    await onRefreshRecord();
                  } catch {
                    // non-fatal refresh failure
                  }
                  dispatch(
                    showToast({ message: "Action saved", type: "success" }),
                  );
                } catch {
                  dispatch(
                    showToast({
                      message: "Failed to save action",
                      type: "error",
                    }),
                  );
                }
              }}
              assigneeOptions={contactOptions}
              projectOptions={projectOptions}
            />
          )}

          {activeTab === "contacts" && (
            <ContactPanel
              contacts={fkContacts}
              isEditing={true}
              loading={fkContactsLoading}
              parent_model={entityType}
              parentId={entityId}
              customer_id={customer_id}
              customer_name={orgDisplayName}
              primaryContactId={primaryContactId}
              onSetPrimary={onSetPrimary}
              onRefresh={onRefreshContacts}
              onChange={onContactsChange}
              onSaveSuccess={onContactSaveSuccess}
            />
          )}

          {activeTab === "documents" && (
            <DocumentsPanel
              parent_model={entityType}
              parentId={entityId}
              data={data?.refs?.links?.document}
              isEditing={mode !== "view" || isEditing}
              onChange={() => {}}
            />
          )}

          {activeTab === "qa" && (
            <QAPanel
              parent_model={entityType}
              parentId={entityId}
              data={data?.qa}
            />
          )}

          {activeTab === "raw" && (
            <RawDataPanel
              entityType={entityType}
              entityId={entityId}
              data={data}
            />
          )}

          {extraTabContent}
        </div>
      </div>
    </div>
  );
}
