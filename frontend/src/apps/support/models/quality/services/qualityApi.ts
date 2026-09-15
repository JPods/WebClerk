/**
 * Quality API — all operations go through wcapi against the Action model.
 * No separate quality model. Action IS the quality record.
 *
 * Alice tracks these via the same Action pipeline she already uses.
 * The quality_type filter in metadata distinguishes quality records from
 * regular actions.
 */
import { getRecords, saveRecord, deleteRecord } from '@/api/wcapi';
import type { QualityType, QualityMetadata } from '../types/qualityTypes';
import { QUALITY_PREFIX } from '../types/qualityTypes';

const MODEL = 'action';

// ── Helpers ──────────────────────────────────────────────────────────

/** Generate next quality number: NCR-001, CAR-002, etc. */
export async function nextQualityNumber(qualityType: QualityType): Promise<string> {
  const prefix = QUALITY_PREFIX[qualityType];
  const res = await getRecords(MODEL, {
    filters: { 'metadata__quality_type': qualityType },
    order_by: '-id',
    limit: 1,
  });
  const last = res.results?.[0];
  if (last?.metadata?.quality_number) {
    const num = parseInt(last.metadata.quality_number.split('-')[1] || '0', 10);
    return `${prefix}-${String(num + 1).padStart(3, '0')}`;
  }
  return `${prefix}-001`;
}

// ── CRUD ─────────────────────────────────────────────────────────────

export async function createQualityRecord(
  qualityType: QualityType,
  task: string,
  description: string,
  metadata: QualityMetadata,
  extra?: Record<string, any>,
) {
  return saveRecord(MODEL, {
    task,
    description,
    status: 'open',
    project_name: 'Quality',
    metadata: {
      ...metadata,
      quality_type: qualityType,
    },
    ...extra,
  });
}

export async function updateQualityRecord(
  id: number,
  updates: Record<string, any>,
) {
  return saveRecord(MODEL, { id, ...updates });
}

export async function deleteQualityRecord(id: number) {
  return deleteRecord(MODEL, id);
}

// ── Queries ──────────────────────────────────────────────────────────

/** Fetch all quality records of a given type */
export async function fetchQualityRecords(
  qualityType?: QualityType,
  params?: Record<string, any>,
) {
  const filters: Record<string, any> = {
    ...params?.filters,
  };
  if (qualityType) {
    filters['metadata__quality_type'] = qualityType;
  } else {
    // All quality records — any type
    filters['metadata__quality_type__isnull'] = false;
  }
  const res = await getRecords(MODEL, { ...params, filters });
  return res.results || [];
}

/** Fetch a single quality record by ID */
export async function fetchQualityRecord(id: number) {
  const res = await getRecords(MODEL, { filters: { id } });
  return res.results?.[0] || null;
}

/** Fetch open quality records for the dashboard */
export async function fetchOpenQuality() {
  return fetchQualityRecords(undefined, {
    filters: { status: 'open' },
    order_by: '-dt_created',
  });
}

/** Advance workflow step */
export async function advanceWorkflow(
  id: number,
  nextStep: string,
  updates?: Record<string, any>,
) {
  const record = await fetchQualityRecord(id);
  if (!record) throw new Error(`Quality record ${id} not found`);
  const metadata = { ...record.metadata, workflow_step: nextStep, ...updates };
  return saveRecord(MODEL, { id, metadata });
}

/** Spawn a child Action (e.g., CAR from NCR, new CAR from failed verification) */
export async function spawnChildAction(
  parentId: number,
  childType: QualityType,
  task: string,
  description: string,
  metadata: QualityMetadata,
) {
  return saveRecord(MODEL, {
    task,
    description,
    status: 'open',
    project_name: 'Quality',
    parent_action: parentId,
    metadata: {
      ...metadata,
      quality_type: childType,
    },
  });
}
