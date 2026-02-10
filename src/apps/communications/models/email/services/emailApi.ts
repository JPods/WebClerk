/**
 * Email API - Uses centralized wcapi endpoints
 */
import { getRecords, getRecord, saveRecord, deleteRecord } from "@/api/wcapi";
import type {
  CreateEmailRequest,
  EmailApiTask,
  UpdateEmailRequest,
} from "../types/emailType";

const MODEL_NAME = "email";

export const createEmail = async (
  payload: CreateEmailRequest
): Promise<EmailApiTask> => {
  return saveRecord(MODEL_NAME, payload);
};

export const updateEmail = async (
  payload: UpdateEmailRequest
): Promise<EmailApiTask> => {
  return saveRecord(MODEL_NAME, payload);
};

export const deleteEmail = async (_model_name: string, id: number) => {
  return deleteRecord(MODEL_NAME, id);
};

export const fetchEmails = async (id?: number) => {
  if (id) {
    return getRecord(MODEL_NAME, id);
  }
  return getRecords(MODEL_NAME);
};
