/* LastChecked: 2026-08-18 | WhereUsed: TransactionDetail, OrgDetail | WhoCreated: Claude */
/**
 * PanelSectionRenderer — renders a single collapsible panel section.
 *
 * Delegates to TabContent (from TabsRenderer) for the actual content,
 * wrapped in a CollapsiblePanel for always-visible, collapsible display.
 */
import React from 'react';
import type { PanelSection } from '@/hooks/useDetailLayout';
import { TabContent } from './TabsRenderer';
import CollapsiblePanel from '@/apps/common/components/CollapsiblePanel';

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
