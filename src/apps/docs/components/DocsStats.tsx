/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { docsApi } from '../services/docsApi';
import type { DocsStats as DocsStatsType } from '../types/docsTypes';

export const DocsStats: React.FC = () => {
  const [stats, setStats] = useState<DocsStatsType | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const data = await docsApi.getStats();
        setStats(data);
      } catch (err) {
        setError('Failed to load stats');
        console.error('Error fetching docs stats:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchStats();
  }, []);

  const handleNavigate = (path: string) => {
    navigate(path);
  };

  if (loading) {
    return <div className="docs-stats-loading">Loading stats...</div>;
  }

  if (error) {
    return <div className="docs-stats-error">{error}</div>;
  }

  return (
    <div className="docs-stats">
      <h3>Documentation Overview</h3>
      <div className="stats-grid">
        <div className="stat-item">
          <div className="stat-count">{stats?.documents || 0}</div>
          <div className="stat-label">Documents</div>
          <button
            className="stat-button"
            onClick={() => handleNavigate('/docs/documents')}
          >
            View Documents
          </button>
        </div>
        <div className="stat-item">
          <div className="stat-count">{stats?.linkages || 0}</div>
          <div className="stat-label">Linkages</div>
          <button
            className="stat-button"
            onClick={() => handleNavigate('/docs/linkages')}
          >
            View Linkages
          </button>
        </div>
        <div className="stat-item">
          <div className="stat-count">{stats?.question_answers || 0}</div>
          <div className="stat-label">Q&A Records</div>
          <button
            className="stat-button"
            onClick={() => handleNavigate('/docs/question-answers')}
          >
            View Q&A
          </button>
        </div>
      </div>
    </div>
  );
};

export default DocsStats;