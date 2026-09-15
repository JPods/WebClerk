/**
 * JsonSchemaReference — printable JSON envelope reference for all models.
 *
 * Route: /json-schema
 * Shows every model's envelope structure in a print-friendly layout.
 * Users can print this page or Cmd+P from the browser.
 */
import React from 'react';
import { JsonSchemaTree, ENVELOPE_SCHEMAS } from '@/components/widgets/JsonSchemaTree';

const MODEL_GROUPS: { title: string; models: string[] }[] = [
  {
    title: 'Transaction Headers',
    models: ['invoice', 'order', 'proposal', 'purchase', 'workorder'],
  },
  {
    title: 'Transaction Lines',
    models: ['invoice_line', 'order_line', 'proposal_line', 'purchase_line', 'workorder_line'],
  },
  {
    title: 'Payments & Accounts',
    models: ['payment', 'payment_application', 'ledger', 'paymentterm', 'taxjurisdiction'],
  },
  {
    title: 'Core Models',
    models: ['contact', 'item', 'serial', 'action', 'setting', 'pending', 'orgbase'],
  },
  {
    title: 'Products',
    models: ['receipt', 'bom', 'project', 'statement_line'],
  },
  {
    title: 'Documents & Reports',
    models: ['document', 'tag', 'questionanswer', 'report'],
  },
  {
    title: 'Sync & Conversion',
    models: ['connection', 'bundle', 'conversionproject'],
  },
  {
    title: 'Scheduler',
    models: ['scheduledtask', 'taskrun'],
  },
];

export default function JsonSchemaReference() {
  // Deduplicate shared schemas — show one representative per group
  const sharedSchemas = new Map<ModelSchema, string[]>();
  type ModelSchema = typeof ENVELOPE_SCHEMAS[string];

  for (const group of MODEL_GROUPS) {
    for (const model of group.models) {
      const schema = ENVELOPE_SCHEMAS[model];
      if (!schema) continue;
      const existing = sharedSchemas.get(schema);
      if (existing) { existing.push(model); }
      else { sharedSchemas.set(schema, [model]); }
    }
  }

  return (
    <div style={{ maxWidth: 900, margin: '0 auto', padding: '24px 32px', fontFamily: 'system-ui, sans-serif' }}>
      <style>{`
        @media print {
          body { margin: 0; }
          .no-print { display: none !important; }
          .page-break { page-break-before: always; }
        }
      `}</style>

      <div className="no-print" style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h1 style={{ fontSize: 20, fontWeight: 700, margin: 0 }}>JSON Envelope Reference</h1>
        <button
          onClick={() => window.print()}
          style={{
            padding: '6px 16px', borderRadius: 4, border: '1px solid #e2e8f0',
            background: '#f8fafc', cursor: 'pointer', fontSize: 13,
          }}
        >
          Print
        </button>
      </div>

      <div style={{ marginBottom: 24, fontSize: 13, color: '#475569', lineHeight: 1.6 }}>
        <strong>Rule:</strong> JSON envelope is the single source of truth.
        Scalar fields (<code>total</code>, <code>balance</code>) are denormalized query indexes — never
        read them for display or computation. Use <code>totals.total</code> not <code>total</code>.
      </div>

      {MODEL_GROUPS.map((group, gi) => {
        // Find the first model with a schema to show as representative
        const representative = group.models.find(m => ENVELOPE_SCHEMAS[m]);
        if (!representative) return null;
        const schema = ENVELOPE_SCHEMAS[representative];
        // Which models share this exact schema object?
        const sharing = group.models.filter(m => ENVELOPE_SCHEMAS[m] === schema);
        // Any models with their own unique schema?
        const unique = group.models.filter(m => ENVELOPE_SCHEMAS[m] && ENVELOPE_SCHEMAS[m] !== schema);

        return (
          <div key={group.title} className={gi > 0 ? 'page-break' : ''}>
            <div style={{ marginTop: gi > 0 ? 32 : 0, marginBottom: 8, fontSize: 16, fontWeight: 700, color: '#1e293b' }}>
              {group.title}
            </div>
            {sharing.length > 1 && (
              <div style={{ fontSize: 12, color: '#64748b', marginBottom: 12 }}>
                Shared schema — applies to: {sharing.join(', ')}
              </div>
            )}
            <JsonSchemaTree modelName={representative} printMode />

            {unique.map(model => (
              <div key={model} style={{ marginTop: 24 }}>
                <div style={{ fontSize: 13, fontWeight: 600, color: '#334155', marginBottom: 4 }}>
                  {ENVELOPE_SCHEMAS[model].label} — additional fields
                </div>
                <JsonSchemaTree modelName={model} printMode />
              </div>
            ))}
          </div>
        );
      })}
    </div>
  );
}
