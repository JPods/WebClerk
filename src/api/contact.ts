/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import apiClient from "./axios";
import { PostLoginURL } from "../routes/network";
import type { CreateContactRequest, ContactApiTask } from "../type/contact";

const unwrap = <T>(response: any): T => {
  if (!response) return [] as unknown as T;
  if (response.data?.data) return response.data.data as T;
  if (response.data) return response.data as T;
  return response as T;
};
//await apiClient.get(PostLoginURL.allTypes + 'model_name=contact' + (id ? `&id=${id}` : '') );
export const createContact = async (
  payload: CreateContactRequest
): Promise<ContactApiTask> => {
  const model_name: string = "contact";
  const res = await apiClient.post(PostLoginURL.allSave, {
    ...payload,
    model_name,
  });
  return unwrap<ContactApiTask>(res);
};

export const fetchContacts = async (id: any = "") => {
  try {
    const res = await apiClient.get(
      PostLoginURL.allTypes + "?model_name=contact" + (id ? `&id=${id}` : "")
    );
    return res;
  } catch (error: any) {
    return error.response?.data || error.message;
  }
};

export const fetchContact = async (): Promise<ContactApiTask[]> => {
  const res = await apiClient.get(PostLoginURL.allTypes + "model_name=contact");
  return unwrap<ContactApiTask[]>(res);
};
