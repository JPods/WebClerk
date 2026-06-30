/**
 * QAPrint — printable QA / Condition Report.
 * Matches vue2020 QAPrint.vue layout.
 * Route: /transactions/qa/print/:model/:id
 */
import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { getRecords } from '@/api/wcapi';
import { S, PRINT_CSS } from './printStyles';

export default function QAPrint() {
  const { model, id } = useParams<{ model: string; id: string }>();
  const [qaItems, setQaItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!model || !id) return;
    (async () => {
      try {
        const res = await getRecords('question_answer', {
          parent_model: model,
          parent_id: id,
          ordering: 'sequence',
        }) as any;
        setQaItems(res?.results || []);
      } catch (e) { console.error('Failed to load QA:', e); }
      finally { setLoading(false); }
    })();
  }, [model, id]);

  useEffect(() => {
    const style = document.createElement('style');
    style.textContent = PRINT_CSS;
    document.head.appendChild(style);
    return () => { document.head.removeChild(style); };
  }, []);

  if (loading) return <div style={{ padding: 40, textAlign: 'center' }}>Loading QA report...</div>;

  return (
    <div style={S.page}>
      <button className="no-print" style={S.printBtn} onClick={() => window.print()}>Print Report</button>

      {/* Header */}
      <div style={S.header}>
        <div style={S.headerLeft}>
          <img src="/img/logo.png" alt="Logo" style={S.logo} onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }} />
        </div>
        <div style={S.headerRight}>
          <div style={S.docTitle}>Condition Report</div>
          <div style={{ fontSize: 12, color: '#666' }}>{model} #{id}</div>
        </div>
      </div>

      {/* QA Items */}
      {qaItems.length === 0 && (
        <div style={{ padding: 24, textAlign: 'center', color: '#999' }}>No QA records found.</div>
      )}

      {qaItems.map((qa: any, i: number) => (
        <div key={qa.id || i} style={{ display: 'flex', gap: 16, padding: '12px 0', borderBottom: '1px solid #eee' }}>
          {/* Image (if available in metadata) */}
          {qa.metadata?.images?.[0] && (
            <div style={{ flexShrink: 0 }}>
              <img
                src={qa.metadata.images[0]}
                alt={`QA ${i + 1}`}
                style={{ width: 144, height: 144, objectFit: 'cover', borderRadius: 4, border: '1px solid #ddd' }}
                onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
              />
            </div>
          )}

          {/* Q&A content */}
          <div style={{ flex: 1 }}>
            <div style={{ display: 'flex', gap: 16, marginBottom: 4 }}>
              <span style={{ fontSize: 10, color: '#999', fontWeight: 600 }}>#{qa.sequence || i + 1}</span>
              {qa.status && <span style={{ fontSize: 10, color: qa.status === 'pass' ? '#198754' : qa.status === 'fail' ? '#dc3545' : '#666', fontWeight: 600 }}>{qa.status.toUpperCase()}</span>}
            </div>
            <div style={{ fontSize: 12, fontWeight: 600, color: '#333', marginBottom: 4 }}>
              {qa.question || '--'}
            </div>
            <div style={{ fontSize: 12, color: '#555', lineHeight: 1.5 }}>
              {qa.answer || '--'}
            </div>
            {qa.answered_by?.attention && (
              <div style={{ fontSize: 10, color: '#999', marginTop: 4 }}>Answered by: {qa.answered_by.attention}</div>
            )}
          </div>
        </div>
      ))}

      {/* Footer */}
      <div style={{ ...S.footer, display: 'flex', justifyContent: 'space-between', fontSize: 10, color: '#999' }}>
        <span>{qaItems.length} items</span>
        <span>{model} #{id}</span>
        <span>{new Date().toLocaleDateString()}</span>
      </div>
    </div>
  );
}
