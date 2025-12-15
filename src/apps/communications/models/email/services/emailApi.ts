import apiClient from "../../../../../api/axios";
import { getRecords, saveRecord, deleteRecord } from "../../../../../api/wcapi";
import { PostLoginURL } from "../../../../../routes/network";
export const createEmail = async (data: any) => {
  return saveRecord("email", data);
};

export const updateEmail = async (data: any) => {
  return saveRecord("email", data);
};

// export const deleteEmail = async (id: number) => {
//   return deleteRecord("email", id);

// };
export const deleteEmail = async (model_name: string, id: number) => {
  try {
    const res = await apiClient.post(PostLoginURL.allSave, {
      model_name,
      id,
      mode: "delete",
    });
    return res;
  } catch (error) {
    const axiosError = error as any;
    return axiosError.response?.data || axiosError.message;
  }
};

export const fetchEmails = async (id: number) => {
  try {
    const res = await apiClient.get(
      PostLoginURL.allTypes + "model_name=email" + (id ? `&id=${id}` : "")
    );
    return res;
  } catch (error: any) {
    return error.response?.data || error.message;
  }
};
