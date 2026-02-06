/**
 * QATab - Transaction Q&A tab using QAPanel
 * 
 * Displays template-based questions from Settings organized by scope:
 * - Global: applies to all models (model_target is null)
 * - App-level: applies to all models in the same app (e.g., "transactions")
 * - Model-specific: applies only to this model type
 *
 * When API persistence is configured (transactionType + transactionId),
 * answers are saved to the database.
 */
import React, { useState, useEffect } from "react";
import { QAPanel, getScopedQAQuestionGroups, getAppForModel, type ScopedQAGroups } from "@/apps/common/components/panels";

interface QATabProps {
  /** Transaction type for API persistence (e.g., "order", "purchase") */
  transactionType?: string;
  /** Transaction ID for API persistence */
  transactionId?: number;
  /** Question group name for template questions */
  questionGroup?: string;
  /** Whether user can edit */
  canEdit?: boolean;
}

const QATab: React.FC<QATabProps> = ({
  transactionType,
  transactionId,
  questionGroup: initialGroup,
  canEdit = true,
}) => {
  const [scopedGroups, setScopedGroups] = useState<ScopedQAGroups>({ global: [], appLevel: [], modelSpecific: [], all: [] });
  const [selectedGroup, setSelectedGroup] = useState<string>(initialGroup || '');
  const [isLoading, setIsLoading] = useState(true);

  // Get app name for display
  const appName = transactionType ? getAppForModel(transactionType) : null;
  const appLabel = appName ? appName.charAt(0).toUpperCase() + appName.slice(1) : 'App';
  const modelLabel = transactionType ? transactionType.charAt(0).toUpperCase() + transactionType.slice(1) : 'Model';

  // Load available question groups scoped to this model
  useEffect(() => {
    async function loadGroups() {
      setIsLoading(true);
      const groups = await getScopedQAQuestionGroups(transactionType);
      setScopedGroups(groups);
      // Don't auto-select - user must explicitly choose a group
      setIsLoading(false);
    }
    loadGroups();
  }, [transactionType]);

  // If we have both transactionType and transactionId, use API persistence
  const hasApiPersistence = !!(transactionType && transactionId);

  if (isLoading) {
    return (
      <div className="w-full mt-4 p-6 bg-white dark:bg-slate-800 rounded-lg border text-center text-slate-400">
        Loading question groups...
      </div>
    );
  }

  const hasModelSpecific = scopedGroups.modelSpecific.length > 0;
  const hasAppLevel = scopedGroups.appLevel.length > 0;
  const hasGlobal = scopedGroups.global.length > 0;

  return (
    <div className="w-full mt-4 space-y-4">
      {/* Question Group Selector with scope labels */}
      <div className="flex items-center gap-3 px-1">
        <label className="text-sm font-medium text-slate-600 dark:text-slate-400">
          Question Group:
        </label>
        <select
          value={selectedGroup}
          onChange={(e) => setSelectedGroup(e.target.value)}
          className="px-3 py-1.5 text-sm border border-slate-300 dark:border-slate-600 rounded-md bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:ring-2 focus:ring-indigo-500 min-w-[200px]"
        >
          <option value="">-- Select Group --</option>
          
          {/* Model-specific groups first */}
          {hasModelSpecific && (
            <optgroup label={`${modelLabel} Only`}>
              {scopedGroups.modelSpecific.map((group) => (
                <option key={group.id} value={group.name}>
                  {group.name}
                </option>
              ))}
            </optgroup>
          )}
          
          {/* App-level groups */}
          {hasAppLevel && (
            <optgroup label={`All ${appLabel}`}>
              {scopedGroups.appLevel.map((group) => (
                <option key={group.id} value={group.name}>
                  {group.name}
                </option>
              ))}
            </optgroup>
          )}
          
          {/* Global groups */}
          {hasGlobal && (
            <optgroup label="All Models">
              {scopedGroups.global.map((group) => (
                <option key={group.id} value={group.name}>
                  {group.name}
                </option>
              ))}
            </optgroup>
          )}
        </select>
        
        <span className="text-xs text-slate-400">
          {scopedGroups.all.length} groups
        </span>
      </div>

      {/* QA Panel */}
      {selectedGroup ? (
        <QAPanel
          key={selectedGroup} // Force remount when group changes
          title={selectedGroup}
          questionGroup={selectedGroup}
          parentType={hasApiPersistence ? transactionType : undefined}
          parentId={hasApiPersistence ? transactionId : undefined}
          readOnly={!canEdit}
          defaultCollapsed={false}
        />
      ) : (
        <div className="p-6 bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 text-center text-slate-400">
          Select a question group to view Q&A
        </div>
      )}
    </div>
  );
};

export default QATab;
