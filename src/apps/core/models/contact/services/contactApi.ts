import { getRecords, saveRecord, deleteRecord } from "@/api/wcapi";
import type {
  CreateContactRequest,
  ContactApiTask,
  UpdateContactRequest,
} from "../types/contactType";

export const createContact = async (
  payload: CreateContactRequest
): Promise<ContactApiTask> => {
  const res = await saveRecord("contact", payload);
  return res;
};

export const updateContact = async (
  payload: UpdateContactRequest
): Promise<ContactApiTask> => {
  const res = await saveRecord("contact", payload);
  return res;
};

export const deleteContact = async (id: number) => {
  return deleteRecord("contact", id);
};

export const fetchContacts = async (params?: any) => {
  const res = await getRecords("contact", params);
  return { status: 200, data: { items: res.results || [] } };
};

export const fetchContact = async (): Promise<ContactApiTask[]> => {
  const res = await getRecords("contact");
  return res.results || [];
};
