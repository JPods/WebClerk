/**
 * QATab - Transaction Q&A tab using QAPanel
 * 
 * Displays template-based questions from Settings organized by scope:
 * - Global: applies to all models (parent_model is null)
 * - App-level: applies to all models in the same app (e.g., "transactions")
 * - Model-specific: applies only to this model type
 *
 * When API persistence is configured (transactionType + transactionId),
 * answers are saved to the database.
 * 
 * Flow:
 * 1. User selects a question group from dropdown
 * 2. Confirmation modal shows the questions that will be created
 * 3. On confirm, QA records are created in the backend with status='open'
 * 4. QAPanel then loads and displays those records for answering
 */
import React, { useState, useEffect } from "react";
import { FaQuestionCircle, FaSpinner, FaCheck, FaTimes, FaExclamationTriangle } from "react-icons/fa";
import { 
  QAPanel, 
  getScopedQAQuestionGroups, 
  getAppForModel, 
  getQAQuestions,
  applyQuestionGroup,
  type ScopedQAGroups,
  type QAQuestionsSetting,
} from "../../common/components/panels";

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

// ---------------------------------------------------------------------------
// Confirmation Modal for Question Group Selection
// ---------------------------------------------------------------------------

interface ConfirmGroupModalProps {
  isOpen: boolean;
  groupSetting: QAQuestionsSetting | null;
  onConfirm: () => void;
  onCancel: () => void;
  isCreating: boolean;
  error: string | null;
}

const ConfirmGroupModal: React.FC<ConfirmGroupModalProps> = ({
  isOpen,
  groupSetting,
  onConfirm,
  onCancel,
  isCreating,
  error,
}) => {
  if (!isOpen || !groupSetting) return null;

  const questions = groupSetting.data?.questions || [];

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-slate-800 rounded-lg p-4 w-96 max-w-full mx-4 shadow-xl max-h-[80vh] flex flex-col">
        <div className="flex items-center gap-2 mb-3 text-indigo-600 dark:text-indigo-400">
          <FaQuestionCircle size={16} />
          <h3 className="text-sm font-semibold">Apply Question Group</h3>
        </div>
        
        <div className="mb-3">
          <p className="text-xs text-slate-600 dark:text-slate-400 mb-2">
            Apply <span className="font-semibold text-slate-800 dark:text-slate-200">"{groupSetting.name}"</span> to this record?
          </p>
          <p className="text-xs text-slate-500 dark:text-slate-500 mb-2">
            The following {questions.length} question{questions.length !== 1 ? 's' : ''} will be created:
          </p>
        </div>

        <div className="flex-1 overflow-y-auto mb-3 border border-slate-200 dark:border-slate-700 rounded p-2 bg-slate-50 dark:bg-slate-900/50">
          <ul className="space-y-1">
            {questions.map((q, idx) => (
              <li key={q.id} className="text-xs text-slate-600 dark:text-slate-400 flex items-start gap-1.5">
                <span className="text-slate-400 font-mono text-[10px] w-4 flex-shrink-0">{idx + 1}.</span>
                <span>{q.question}</span>
              </li>
            ))}
          </ul>
        </div>

        {/* Error message */}
        {error && (
          <div className="mb-3 p-2 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-700 rounded text-xs text-red-700 dark:text-red-300 flex items-center gap-2">
            <FaTimes size={10} />
            <span>{error}</span>
          </div>
        )}

        <div className="flex justify-end gap-2 pt-2 border-t border-slate-200 dark:border-slate-700">
          <button
            type="button"
            onClick={onCancel}
            disabled={isCreating}
            className="px-3 py-1.5 text-xs text-slate-600 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-700 rounded disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={isCreating}
            className="px-3 py-1.5 text-xs bg-indigo-500 text-white rounded hover:bg-indigo-600 disabled:opacity-50 flex items-center gap-1"
          >
            {isCreating ? <FaSpinner className="animate-spin" size={10} /> : <FaCheck size={10} />}
            Create Questions
          </button>
        </div>
      </div>
    </div>
  );
};

const QATab: React.FC<QATabProps> = ({
  transactionType,
  transactionId,
  questionGroup: initialGroup,
  canEdit = true,
}) => {
  const [scopedGroups, setScopedGroups] = useState<ScopedQAGroups>({ global: [], appLevel: [], modelSpecific: [], all: [] });
  const [selectedGroup, setSelectedGroup] = useState<string>(initialGroup || '');
  const [confirmedGroup, setConfirmedGroup] = useState<string>('');
  const [isLoading, setIsLoading] = useState(true);
  
  // Confirmation modal state
  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const [pendingGroupName, setPendingGroupName] = useState<string>('');
  const [pendingGroupSetting, setPendingGroupSetting] = useState<QAQuestionsSetting | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [panelKey, setPanelKey] = useState(0); // Force remount after creation

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

  // Handle group selection from dropdown
  const handleGroupSelect = async (groupName: string) => {
    if (!groupName) {
      setSelectedGroup('');
      return;
    }

    // If no API persistence, just show the panel without creating records
    if (!hasApiPersistence) {
      setSelectedGroup(groupName);
      setConfirmedGroup(groupName);
      return;
    }

    // Fetch the group details to show in confirmation
    setPendingGroupName(groupName);
    const setting = await getQAQuestions(groupName);
    if (setting) {
      setPendingGroupSetting(setting);
      setShowConfirmModal(true);
    } else {
      // Group not found, show error or just select it
      console.error(`Question group "${groupName}" not found`);
      setSelectedGroup(groupName);
    }
  };

  // Handle confirmation - call backend service to create all QA records
  const handleConfirmGroup = async () => {
    if (!pendingGroupSetting || !transactionType || !transactionId) return;

    setIsCreating(true);
    setCreateError(null);
    
    try {
      // Call backend service to create all QA records atomically
      const result = await applyQuestionGroup(
        pendingGroupSetting.name,
        pendingGroupSetting.id,
        transactionType,
        transactionId
      );

      console.log(`Created ${result.created_count} QA records, ${result.existing_count} existing`);

      // Close modal and show the panel
      setShowConfirmModal(false);
      setSelectedGroup(pendingGroupName);
      setConfirmedGroup(pendingGroupName);
      setPendingGroupName('');
      setPendingGroupSetting(null);
      setPanelKey(prev => prev + 1); // Force QAPanel to remount and reload
    } catch (err: any) {
      console.error('Failed to create QA records:', err);
      // Extract error message - handle both string and object error formats
      let message = 'Failed to create questions';
      const errData = err?.response?.data?.error;
      if (typeof errData === 'string') {
        message = errData;
      } else if (errData?.details) {
        message = errData.details;
      } else if (errData?.code) {
        message = errData.code;
      } else if (err?.message) {
        message = err.message;
      }
      setCreateError(message);
    } finally {
      setIsCreating(false);
    }
  };

  // Handle cancel - reset pending state
  const handleCancelGroup = () => {
    setShowConfirmModal(false);
    setPendingGroupName('');
    setPendingGroupSetting(null);
    setCreateError(null);
    // Reset dropdown to current confirmed group
    setSelectedGroup(confirmedGroup);
  };

  // Show warning if parent record not saved
  if (!hasApiPersistence) {
    return (
      <div className="w-full mt-2 p-4 bg-amber-50 dark:bg-amber-900/20 rounded-lg border border-amber-200 dark:border-amber-700 flex items-center gap-2">
        <FaExclamationTriangle className="text-amber-600 dark:text-amber-400" size={14} />
        <p className="text-sm text-amber-700 dark:text-amber-300">
          Save the record first to enable Q&A functionality.
        </p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="w-full mt-2 p-4 bg-white dark:bg-slate-800 rounded-lg border text-center text-slate-400">
        Loading question groups...
      </div>
    );
  }

  const hasModelSpecific = scopedGroups.modelSpecific.length > 0;
  const hasAppLevel = scopedGroups.appLevel.length > 0;
  const hasGlobal = scopedGroups.global.length > 0;

  return (
    <div className="w-full mt-2 space-y-2">
      {/* Question Group Selector with scope labels */}
      <div className="flex items-center gap-2 px-1">
        <label className="text-sm font-medium text-slate-600 dark:text-slate-400">
          Question Group:
        </label>
        <select
          value={selectedGroup}
          onChange={(e) => handleGroupSelect(e.target.value)}
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

      {/* QA Panel - only show after group is confirmed */}
      {confirmedGroup ? (
        <QAPanel
          key={`${confirmedGroup}-${panelKey}`} // Force remount when group changes or after creation
          title={confirmedGroup}
          questionGroup={confirmedGroup}
          parentModel={transactionType}
          parentId={transactionId}
          readOnly={!canEdit}
          defaultCollapsed={false}
        />
      ) : (
        <div className="p-4 bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 text-center text-slate-400">
          Select a question group to view Q&A
        </div>
      )}

      {/* Confirmation Modal */}
      <ConfirmGroupModal
        isOpen={showConfirmModal}
        groupSetting={pendingGroupSetting}
        onConfirm={handleConfirmGroup}
        onCancel={handleCancelGroup}
        isCreating={isCreating}
        error={createError}
      />
    </div>
  );
};

export default QATab;
