import apiClient from "../../../../../axios";
import { PostLoginURL } from "../../../../../../routes/network";
import type {
  CreateCampaignRequest,
  CampaignApiTask,
  UpdateCampaignRequest,
} from "../types/campaignType";

const unwrap = <T>(response: any): T => {
  if (!response) return [] as unknown as T;
  if (response.data?.data) return response.data.data as T;
  if (response.data) return response.data as T;
  return response as T;
};

export const createCampaign = async (
  payload: CreateCampaignRequest
): Promise<CampaignApiTask> => {
  const model_name: string = "campaign";
  const res = await apiClient.post(PostLoginURL.allSave, {
    ...payload,
    model_name,
  });
  return unwrap<CampaignApiTask>(res);
};

export const updateCampaign = async (
  payload: UpdateCampaignRequest
): Promise<CampaignApiTask> => {
  const model_name: string = "campaign";
  const res = await apiClient.post(`${PostLoginURL.allSave}`, {
    ...payload,
    model_name,
  });
  return unwrap<CampaignApiTask>(res);
};

export const deleteCampaign = async (id: any) => {
  try {
    const res = await apiClient.delete(PostLoginURL.allTypes + id + "/");
    return res;
  } catch (error: any) {
    return error.response?.data || error.message;
  }
};

export const fetchCampaigns = async (id: any = "") => {
  try {
    const res = await apiClient.get(
      PostLoginURL.allTypes + "model_name=campaign" + (id ? `&id=${id}` : "")
    );
    return res;
  } catch (error: any) {
    return error.response?.data || error.message;
  }
};

export const fetchCampaign = async (): Promise<CampaignApiTask[]> => {
  const res = await apiClient.get(PostLoginURL.allTypes + "model_name=campaign");
  return unwrap<CampaignApiTask[]>(res);
};