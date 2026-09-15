/**
 * Quality types — Action record views filtered by metadata.quality_type
 *
 * No separate model. Action IS the quality record.
 * WC2 lesson: controlling actions by model fields sucked.
 * WC3: metadata JSON carries the type-specific schema.
 * Alice evolves workflows without database migrations.
 */

// ── Quality type discriminator ──────────────────────────────────────

export type QualityType = 'ncr' | 'car' | 'deviation' | 'dcr' | 'request';

export const QUALITY_LABELS: Record<QualityType, string> = {
  ncr: 'Nonconformance Report',
  car: 'Corrective Action Request',
  deviation: 'Deviation / Waiver',
  dcr: 'Document Change Request',
  request: 'Request for Support',
};

export const QUALITY_PREFIX: Record<QualityType, string> = {
  ncr: 'NCR',
  car: 'CAR',
  deviation: 'DW',
  dcr: 'DCR',
  request: 'REQ',
};

// ── Workflow steps per type ─────────────────────────────────────────

export const WORKFLOW_STEPS: Record<QualityType, string[]> = {
  ncr: ['identify', 'disposition', 'closed'],
  car: ['originate', 'propose', 'respond', 'close_out', 'verify'],
  deviation: ['request', 'manager_review', 'pm_review', 'quality_review', 'customer_review', 'closed'],
  dcr: ['request', 'manager_review', 'author_assigned', 'final_review', 'released'],
  request: ['submitted', 'follow_up', 'response_received', 'processed'],
};

// ── Type-specific metadata schemas (stored in Action.metadata) ──────

export interface QualityMetadataBase {
  quality_type: QualityType;
  quality_number: string;       // NCR-001, CAR-001, etc.
  workflow_step: string;        // current position in WORKFLOW_STEPS
  originator_name: string;
  originator_org: string;
  originator_email: string;
  originator_phone: string;
}

export interface NCRMetadata extends QualityMetadataBase {
  quality_type: 'ncr';
  item_name: string;
  item_qty: number;
  drawing_part_no: string;
  lot_serial_no: string;
  found_during: string;
  item_location: string;
  actual_condition: string;
  required_condition: string;
  disposition: 'rework' | 'scrap' | 'return_to_supplier' | 'repair' | 'regrade' | 'use_as_is' | '';
  disposition_rationale: string;
  cause: 'design' | 'manufacturing' | 'supplier' | 'training' | 'other' | '';
  cause_explain: string;
  disposition_details: string;
  request_waiver: boolean;
  waiver_number: string;
  car_required: boolean;
  car_action_id: number | null;   // FK to child Action (the spawned CAR)
  safety_affected: boolean;
}

export interface CARMetadata extends QualityMetadataBase {
  quality_type: 'car';
  action_type: 'corrective' | 'preventive' | 'audit';
  audit_report_no: string;
  auditee: string;
  point_of_contact: string;
  // Requirement reference
  req_document: string;
  req_revision: string;
  req_paragraph: string;
  req_text: string;
  // Discrepancy
  discrepancy: string;
  objective_evidence: string;
  // Proposed action
  responsible_dept: string;
  responsible_manager: string;
  est_closure_date: string;
  root_cause: string;
  proposed_action: string;
  // Response
  action_taken: string;
  // Verification
  effective: boolean | null;
  verification_reason: string;
  new_car_action_id: number | null;  // spawned CAR if not effective
}

export interface DeviationMetadata extends QualityMetadataBase {
  quality_type: 'deviation';
  request_type: 'deviation' | 'waiver';
  department: string;
  project_name: string;
  subsystem: string;
  documents_affected: Array<{ number: string; revision: string; title: string }>;
  justification: string;
  approvals: Array<{
    role: string;
    required: boolean;
    approved: boolean | null;
    approver: string;
    date: string;
  }>;
}

export interface DCRMetadata extends QualityMetadataBase {
  quality_type: 'dcr';
  department: 'construction' | 'purchasing' | 'engineering' | '';
  action_type: 'new' | 'revision' | 'cancellation' | 'supersedes';
  doc_number: string;
  doc_title: string;
  rev_from: string;
  rev_to: string;
  superseded_doc: string;
  affected_docs: string;
  summary: string;
  detail: string;
  assigned_author: string;
  implemented: boolean;
  effective_date: string;
}

export interface RequestMetadata extends QualityMetadataBase {
  quality_type: 'request';
  target_org: string;
  target_contact: string;
  target_portal_url: string;
  legal_basis: string;
  follow_up_days: number;
  response_received: boolean;
  response_date: string;
  response_summary: string;
}

export type QualityMetadata =
  | NCRMetadata
  | CARMetadata
  | DeviationMetadata
  | DCRMetadata
  | RequestMetadata;

// ── Component props ─────────────────────────────────────────────────

export interface QualityPageProps {
  modeProp?: 'add' | 'edit' | 'view';
  dataProp?: any;
  qualityType?: QualityType;
  hideBreadcrumb?: boolean;
  onSaved?: () => void;
  inline?: boolean;
  onCancelInline?: () => void;
}
