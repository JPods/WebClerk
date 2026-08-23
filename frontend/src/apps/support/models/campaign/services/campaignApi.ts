/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import { getRecords, saveRecord, deleteRecord } from "@/api/wcapi";
import type {
  CreateCampaignRequest,
  CampaignApiTask,
  UpdateCampaignRequest,
} from "../types/campaignType";

export const createCampaign = async (
  payload: CreateCampaignRequest
): Promise<CampaignApiTask> => {
  return saveRecord("campaign", payload);
};

export const updateCampaign = async (
  payload: UpdateCampaignRequest
): Promise<CampaignApiTask> => {
  return saveRecord("campaign", payload);
};

export const deleteCampaign = async (id: number) => {
  return deleteRecord("campaign", id);
};

export const fetchCampaigns = async (params?: any) => {
  const res = await getRecords("campaign", params);
  return { status: 200, data: { items: res.results || [] } };
};

export const fetchCampaign = async (): Promise<CampaignApiTask[]> => {
  const res = await getRecords("campaign");
  return res.results || [];
};