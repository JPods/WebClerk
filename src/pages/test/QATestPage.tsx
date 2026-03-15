/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
/**
 * QA Panel Test Page
 * 
 * Test page for the QAPanel component.
 * Access at: /test/qa
 */
import React, { useState, useEffect } from 'react';
import { QAPanel, getAllQAQuestionGroups, type QAQuestionsSetting } from '../../apps/common/components/panels';

const QATestPage: React.FC = () => {
  const [groups, setGroups] = useState<QAQuestionsSetting[]>([]);
  const [selectedGroup, setSelectedGroup] = useState<string>('Planning');
  const [parentId, setParentId] = useState<number>(1);
  const [isLoading, setIsLoading] = useState(true);

  // Load available groups
  useEffect(() => {
    async function loadGroups() {
      const allGroups = await getAllQAQuestionGroups();
      setGroups(allGroups);
      if (allGroups.length > 0 && !selectedGroup) {
        setSelectedGroup(allGroups[0].name);
      }
      setIsLoading(false);
    }
    loadGroups();
  }, []);

  return (
    <div className="min-h-screen bg-slate-100 dark:bg-slate-900 p-6">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-slate-800 dark:text-white mb-2">
            Q&A Panel Test
          </h1>
          <p className="text-slate-600 dark:text-slate-400">
            Test the QAPanel component with different question groups.
          </p>
        </div>

        {/* Controls */}
        <div className="bg-white dark:bg-slate-800 rounded-lg p-4 mb-6 shadow-sm">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                Question Group
              </label>
              <select
                value={selectedGroup}
                onChange={(e) => setSelectedGroup(e.target.value)}
                className="w-full px-3 py-2 border rounded-lg dark:bg-slate-700 dark:border-slate-600 dark:text-white"
              >
                {groups.map(g => (
                  <option key={g.id} value={g.name}>{g.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                Parent ID (for testing)
              </label>
              <input
                type="number"
                value={parentId}
                onChange={(e) => setParentId(parseInt(e.target.value) || 1)}
                className="w-full px-3 py-2 border rounded-lg dark:bg-slate-700 dark:border-slate-600 dark:text-white"
              />
            </div>
          </div>
        </div>

        {/* Available Groups Info */}
        {!isLoading && (
          <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4 mb-6 text-sm">
            <strong>Available Groups:</strong>{' '}
            {groups.map(g => g.name).join(', ') || 'None loaded'}
          </div>
        )}

        {/* Q&A Panel */}
        {selectedGroup && (
          <QAPanel
            questionGroup={selectedGroup}
            parent_model="test"
            parentId={parentId}
            onAnswersChange={(answers) => {
              console.log('Answers changed:', answers);
            }}
          />
        )}

        {/* Debug Info */}
        <div className="mt-6 bg-slate-200 dark:bg-slate-700 rounded-lg p-4">
          <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-2">
            Debug Info
          </h3>
          <pre className="text-xs text-slate-600 dark:text-slate-400 overflow-auto">
            {JSON.stringify({ selectedGroup, parentId, groupCount: groups.length }, null, 2)}
          </pre>
        </div>
      </div>
    </div>
  );
};

export default QATestPage;
