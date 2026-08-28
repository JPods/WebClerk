/**
 * QualityDashboard.tsx — "Get it done today" list
 *
 * All open quality records sorted by urgency. A customer request and a
 * rejected shipment show up on the same list — both are Action records
 * with metadata.quality_type. Alice surfaces what needs attention NOW.
 *
 * Priority sorts: overdue first, then by priority, then by age.
 */
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router';
import {
  FileWarning, ClipboardCheck, GitBranch, FileText, HelpCircle,
  AlertTriangle,
} from 'lucide-react';

import ComponentCard from '@/components/common/ComponentCard';
import PageBreadcrumb from '@/components/common/PageBreadCrumb';
import { fetchOpenQuality } from '../services/qualityApi';
import type { QualityType } from '../types/qualityTypes';
import { QUALITY_LABELS, QUALITY_PREFIX, WORKFLOW_STEPS } from '../types/qualityTypes';

const TYPE_ICONS: Record<QualityType, any> = {
  ncr: FileWarning,
  car: ClipboardCheck,
  deviation: GitBranch,
  dcr: FileText,
  request: HelpCircle,
};

const TYPE_COLORS: Record<QualityType, string> = {
  ncr: 'text-red-600 bg-red-50',
  car: 'text-orange-600 bg-orange-50',
  deviation: 'text-purple-600 bg-purple-50',
  dcr: 'text-blue-600 bg-blue-50',
  request: 'text-green-600 bg-green-50',
};

export default function QualityDashboard() {
  const navigate = useNavigate();
  const [records, setRecords] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<QualityType | 'all'>('all');

  useEffect(() => {
    fetchOpenQuality()
      .then(setRecords)
      .finally(() => setLoading(false));
  }, []);

  const filtered = filter === 'all'
    ? records
    : records.filter(r => r.metadata?.quality_type === filter);

  // Sort: overdue first, then priority (lower = more urgent), then oldest first
  const now = Date.now();
  const sorted = [...filtered].sort((a, b) => {
    const aOverdue = a.dt_deadline && a.dt_deadline < now ? 1 : 0;
    const bOverdue = b.dt_deadline && b.dt_deadline < now ? 1 : 0;
    if (bOverdue !== aOverdue) return bOverdue - aOverdue;
    if ((a.priority || 5) !== (b.priority || 5)) return (a.priority || 5) - (b.priority || 5);
    return (a.dt_created || 0) - (b.dt_created || 0);
  });

  const counts: Record<string, number> = { all: records.length };
  for (const r of records) {
    const t = r.metadata?.quality_type || 'unknown';
    counts[t] = (counts[t] || 0) + 1;
  }

  return (
    <div data-wc="quality-dashboard" className="p-4">
      <PageBreadcrumb
        pageTitle="Quality — Get It Done Today"
        items={[{ label: 'Support', path: '/support' }]}
      />

      {/* Filter pills */}
      <div className="flex gap-2 mb-4 flex-wrap">
        {(['all', 'ncr', 'car', 'deviation', 'dcr', 'request'] as const).map(t => (
          <button key={t} onClick={() => setFilter(t)}
            className={`px-3 py-1 rounded-full text-xs font-medium transition
              ${filter === t
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}>
            {t === 'all' ? 'All' : QUALITY_LABELS[t]}
            <span className="ml-1 opacity-70">({counts[t] || 0})</span>
          </button>
        ))}
      </div>

      {/* Records list */}
      {loading ? (
        <p className="text-sm text-gray-400">Loading...</p>
      ) : sorted.length === 0 ? (
        <ComponentCard title="All Clear">
          <p className="text-sm text-gray-500">No open quality records. Nice work.</p>
        </ComponentCard>
      ) : (
        <div className="space-y-2">
          {sorted.map(record => {
            const qt: QualityType = record.metadata?.quality_type || 'request';
            const Icon = TYPE_ICONS[qt] || HelpCircle;
            const color = TYPE_COLORS[qt] || 'text-gray-600 bg-gray-50';
            const qnum = record.metadata?.quality_number || '';
            const step = record.metadata?.workflow_step || '';
            const steps = WORKFLOW_STEPS[qt] || [];
            const stepIdx = steps.indexOf(step);
            const isOverdue = record.dt_deadline && record.dt_deadline < now;

            return (
              <div key={record.id}
                   onClick={() => navigate('/support/quality/detail', {
                     state: { data: record, mode: 'edit', qualityType: qt },
                   })}
                   className={`flex items-center gap-3 p-3 rounded-lg border cursor-pointer
                     hover:shadow-md transition ${isOverdue ? 'border-red-300 bg-red-50/30' : 'border-gray-200 bg-white'}`}>

                {/* Type badge */}
                <div className={`p-2 rounded ${color}`}>
                  <Icon size={16} />
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono text-gray-400">{qnum}</span>
                    <span className="text-sm font-medium text-gray-800 truncate">
                      {record.task}
                    </span>
                    {isOverdue && (
                      <span className="flex items-center gap-1 text-xs text-red-600 font-semibold">
                        <AlertTriangle size={12} /> overdue
                      </span>
                    )}
                  </div>
                  <div className="text-xs text-gray-400 mt-0.5">
                    {QUALITY_LABELS[qt]} — step: {step.replace(/_/g, ' ')}
                    {record.assigned_to && ` — ${record.assigned_to}`}
                  </div>
                </div>

                {/* Step progress */}
                <div className="flex gap-0.5">
                  {steps.map((s, i) => (
                    <div key={s}
                         className={`w-2 h-2 rounded-full ${
                           i < stepIdx ? 'bg-green-400' :
                           i === stepIdx ? 'bg-blue-500' :
                           'bg-gray-200'
                         }`}
                         title={s.replace(/_/g, ' ')} />
                  ))}
                </div>

                {/* Priority */}
                <span className={`text-xs font-mono px-2 py-0.5 rounded
                  ${(record.priority || 5) <= 3 ? 'bg-red-100 text-red-700' :
                    (record.priority || 5) <= 6 ? 'bg-yellow-100 text-yellow-700' :
                    'bg-gray-100 text-gray-500'}`}>
                  P{record.priority || 5}
                </span>
              </div>
            );
          })}
        </div>
      )}

      {/* New record buttons */}
      <div className="mt-6 flex gap-2 flex-wrap">
        {(['ncr', 'car', 'deviation', 'dcr', 'request'] as QualityType[]).map(qt => (
          <button key={qt}
            onClick={() => navigate('/support/quality/detail', {
              state: { mode: 'add', qualityType: qt },
            })}
            className="px-3 py-1.5 text-xs font-medium bg-gray-100 text-gray-700
              rounded hover:bg-gray-200 transition">
            + {QUALITY_PREFIX[qt]}
          </button>
        ))}
      </div>
    </div>
  );
}
