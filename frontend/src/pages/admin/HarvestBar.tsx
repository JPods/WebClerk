/* LastChecked: 2026-08-14 | WhereUsed: DataBrowser list pane (statement_line) | WhoCreated: Bill+Claude */
import React from 'react';
import { apiClient } from '../../api/axios';

// ── HarvestBar — folder input + harvest button for StatementLine ──
export const HarvestBar: React.FC<{ onComplete: () => void }> = ({ onComplete }) => {
  const [folder, setFolder] = React.useState(() => localStorage.getItem('db-harvest-folder') || '');
  const [loading, setLoading] = React.useState(false);
  const [result, setResult] = React.useState<any>(null);

  const handleHarvest = async () => {
    if (!folder.trim()) return;
    setLoading(true);
    setResult(null);
    try {
      const res = await apiClient.post('/wcapi/transactions/statements/harvest/', { path: folder.trim() });
      const data = res.data;
      setResult(data);
      localStorage.setItem('db-harvest-folder', folder.trim());
      if (data.lines_loaded > 0) onComplete();
    } catch (err: any) {
      setResult({ error: err.message || 'Harvest failed' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="db-harvest-bar">
      <span className="db-harvest-label">Harvest:</span>
      <input
        type="text"
        value={folder}
        onChange={(e) => setFolder(e.target.value)}
        onKeyDown={(e) => { if (e.key === 'Enter') handleHarvest(); }}
        placeholder="~/Taxes/2025 or drop folder path here"
        className="db-harvest-input"
      />
      <button
        onClick={handleHarvest}
        disabled={loading || !folder.trim()}
        className="db-harvest-btn"
      >
        {loading ? 'Harvesting...' : 'Harvest'}
      </button>
      {result && !result.error && (
        <span className="db-harvest-result">
          {result.lines_loaded} loaded, {result.lines_skipped} skipped
          {result.missing?.length > 0 && (
            <span className="db-harvest-error" style={{ marginLeft: 8 }}>
              ⚠ Missing: {result.missing.join(', ')}
            </span>
          )}
        </span>
      )}
      {result?.error && (
        <span className="db-harvest-error">{result.error}</span>
      )}
    </div>
  );
};

export default HarvestBar;
