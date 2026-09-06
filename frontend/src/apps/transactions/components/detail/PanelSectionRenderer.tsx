/* LastChecked: 2026-09-05 | WhereUsed: TransactionDetail, OrgDetail | WhoCreated: Claude */
/**
 * PanelSectionRenderer — renders a single collapsible panel section.
 *
 * Link-type panels (contacts, documents, touches, actions) use LinkedRecordsPanel
 * for the standard db.columns header with hamburger (≡), count, and assign button.
 * Comments stays as CommentsPanel. Other types fall back to CollapsiblePanel + TabContent.
 */
import React from 'react';
import type { PanelSection } from '@/hooks/useDetailLayout';
import { TabContent } from './TabsRenderer';
import CollapsiblePanel from '@/apps/common/components/CollapsiblePanel';
import { LinkedRecordsPanel } from '@/apps/common/components/panels/LinkedRecordsPanel';

/** Panels that should render as LinkedRecordsPanel with db.columns header */
const LINKED_PANEL_MODELS = new Set(['contacts', 'documents', 'touches', 'actions']);

/** Map panel content name to the linked model name */
const PANEL_TO_MODEL: Record<string, string> = {
  contacts: 'contact',
  documents: 'document',
  touches: 'touch',
  actions: 'action',
};

interface PanelSectionRendererProps {
  section: PanelSection;
  data: any;
  isEditing: boolean;
  modelName: string;
  onChange: (field: string, value: unknown) => void;
  onRefresh: () => void;
  loggedInUserName?: string;
}

const PanelSectionRenderer: React.FC<PanelSectionRendererProps> = ({
  section, data, isEditing, modelName, onChange, onRefresh, loggedInUserName,
}) => {
  // Link-type panels → LinkedRecordsPanel (db.columns header with hamburger + assign)
  if (LINKED_PANEL_MODELS.has(section.content) && data?.id) {
    const linkedModel = PANEL_TO_MODEL[section.content] || section.content;
    return (
      <LinkedRecordsPanel
        linkedModel={linkedModel}
        parentModel={modelName}
        parentId={data.id}
        defaultCollapsed={section.collapsed ?? true}
      />
    );
  }

  // Everything else (comments, financials, etc.) → CollapsiblePanel + TabContent
  return (
    <CollapsiblePanel
      label={section.label}
      storageKey={`panel_${modelName}_${section.content}`}
      defaultCollapsed={section.collapsed ?? false}
    >
      <TabContent
        tabId={section.content}
        data={data}
        isEditing={isEditing}
        modelName={modelName}
        onChange={onChange}
        onRefresh={onRefresh}
        loggedInUserName={loggedInUserName}
      />
    </CollapsiblePanel>
  );
};

export default PanelSectionRenderer;
