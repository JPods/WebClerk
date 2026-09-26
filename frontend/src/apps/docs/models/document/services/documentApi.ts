/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import { getRecords, createRecord, deleteRecord } from "@/api/wcapi";
import type {
  DocumentApiTask,
} from "../types/documentType";

export const deleteDocument = async (id: number) => {
  return deleteRecord("document", id);
};

export const fetchDocuments = async (params?: any) => {
  const res = await getRecords("document", params);
  return { status: 200, data: { items: res.results || [] } };
};

/**
 * Fetch a single document by ID
 * API: wcapi/get/?model_name=document&id=X
 */
export const fetchDocumentById = async (id: number | string) => {
  const res = await getRecords("document", { id });
  return { status: 200, data: { items: res.results || [] } };
};

export const fetchDocument = async (): Promise<DocumentApiTask[]> => {
  const res = await getRecords("document");
  return res.results || [];
};

/**
 * Submit user feedback — tips, corrections, change requests.
 * Creates an AiMessage (kind='feedback', sender→alice).
 * Alice classifies and acts on the content during her review.
 *
 * Called from: GetHelpDialog Feedback button
 * Stored as: AiMessage record (ai_message table)
 * Processed by: Alice nightly review
 */
export const submitFeedback = async (opts: {
  label: string;
  feedback: string;
  field?: string;
  model?: string;
  sourcePath?: string;
  training?: boolean;
}) => {
  const isTrainingNote = opts.training || opts.feedback.startsWith('tn-');
  return createRecord("ai_message", {
    kind: "feedback",
    sender: "user",
    receiver: "alice",
    subject: isTrainingNote ? `Training Note: ${opts.label}` : `Feedback: ${opts.label}`,
    body: opts.feedback,
    context: {
      element: opts.label,
      field: opts.field || undefined,
      model: opts.model || undefined,
      source_path: opts.sourcePath || undefined,
      training_note: isTrainingNote || undefined,
      page: typeof window !== 'undefined' ? window.location.pathname : undefined,
    },
  });
};