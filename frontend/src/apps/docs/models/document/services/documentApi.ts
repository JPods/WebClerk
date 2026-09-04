/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import { getRecords, saveRecord, deleteRecord } from "@/api/wcapi";
import type {
  CreateDocumentRequest,
  DocumentApiTask,
  UpdateDocumentRequest,
} from "../types/documentType";

export const createDocument = async (
  payload: CreateDocumentRequest
): Promise<DocumentApiTask> => {
  const res = await saveRecord("document", payload);
  return res;
};

export const updateDocument = async (
  payload: UpdateDocumentRequest
): Promise<DocumentApiTask> => {
  const res = await saveRecord("document", payload);
  return res;
};

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
 * Creates a Document with purpose='help-alice' and status='pending'.
 * Alice classifies and acts on the content during her review.
 *
 * Called from: GetHelpDialog Feedback button
 * Stored as: Document record (purpose='help-alice', config.feedback=true)
 * Processed by: Alice nightly review
 */
export const submitFeedback = async (opts: {
  label: string;
  feedback: string;
  field?: string;
  model?: string;
  sourcePath?: string;
}) => {
  return saveRecord("document", {
    name: `Feedback: ${opts.label}`,
    purpose: "help-alice",
    description: `User feedback for ${opts.label}`,
    body: opts.feedback,
    status: "pending",
    config: {
      element: opts.label,
      field: opts.field || undefined,
      model: opts.model || undefined,
      source_path: opts.sourcePath || undefined,
      feedback: true,
    },
  });
};