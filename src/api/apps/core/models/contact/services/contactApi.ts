import apiClient from "../../../../../axios";
import { PostLoginURL } from "../../../../../../routes/network";
import type {
  CreateContactRequest,
  ContactApiTask,
  UpdateContactRequest,
} from "../types/contactType";

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

export const updateContact = async (
  payload: UpdateContactRequest
): Promise<ContactApiTask> => {
  const model_name: string = "contact";
  const res = await apiClient.post(`${PostLoginURL.allSave}`, {
    ...payload,
    model_name,
  });
  return unwrap<ContactApiTask>(res);
};

export const deleteContact = async (id: any) => {
  try {
    const res = await apiClient.delete(PostLoginURL.allTypes + id + "/");
    return res;
  } catch (error: any) {
    return error.response?.data || error.message;
  }
};

export const fetchContacts = async (id: any = "") => {
  try {
    const res = await apiClient.get(
      PostLoginURL.allTypes + "model_name=contact" + (id ? `&id=${id}` : "")
    );
    const payload = unwrap<any>(res);
    if (payload && typeof payload === "object" && !Array.isArray(payload)) {
      return { data: payload };
    }
    if (Array.isArray(payload)) {
      return { data: { results: payload } };
    }
    return { data: { results: [] } };
  } catch (error: any) {
    const payload = unwrap<any>(error?.response);
    if (payload && typeof payload === "object" && !Array.isArray(payload)) {
      return { data: payload };
    }
    if (Array.isArray(payload)) {
      return { data: { results: payload } };
    }
    return { data: { results: [] } };
  }
};

export const fetchContact = async (): Promise<ContactApiTask[]> => {
  const res = await apiClient.get(PostLoginURL.allTypes + "model_name=contact");
  return unwrap<ContactApiTask[]>(res);
};
