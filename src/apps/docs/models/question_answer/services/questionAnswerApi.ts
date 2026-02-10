import apiClient from "../../../../../api/axios";
import { PostLoginURL } from "../../../../../routes/network";
import { deleteRecord } from "@/api/wcapi";
import type {
  CreateQuestionAnswerRequest,
  QuestionAnswerApiTask,
  UpdateQuestionAnswerRequest,
} from "../types/questionAnswerType";

const unwrap = <T>(response: any): T => {
  if (!response) return [] as unknown as T;
  if (response.data?.data) return response.data.data as T;
  if (response.data) return response.data as T;
  return response as T;
};

export const createQuestionAnswer = async (
  payload: CreateQuestionAnswerRequest
): Promise<QuestionAnswerApiTask> => {
  const model_name: string = "question_answer";
  const res = await apiClient.post(PostLoginURL.allSave, {
    ...payload,
    model_name,
  });
  return unwrap<QuestionAnswerApiTask>(res);
};

export const updateQuestionAnswer = async (
  payload: UpdateQuestionAnswerRequest
): Promise<QuestionAnswerApiTask> => {
  const model_name: string = "question_answer";
  const res = await apiClient.post(`${PostLoginURL.allSave}`, {
    ...payload,
    model_name,
  });
  return unwrap<QuestionAnswerApiTask>(res);
};

export const deleteQuestionAnswer = async (id: number) => {
  return deleteRecord("question_answer", id);
};

export const fetchQuestionAnswers = async (id: any = "") => {
  try {
    const res = await apiClient.get(
      PostLoginURL.allTypes + "model_name=question_answer" + (id ? `&id=${id}` : "")
    );
    return res;
  } catch (error: any) {
    return error.response?.data || error.message;
  }
};

export const fetchQuestionAnswer = async (): Promise<QuestionAnswerApiTask[]> => {
  const res = await apiClient.get(PostLoginURL.allTypes + "model_name=question_answer");
  return unwrap<QuestionAnswerApiTask[]>(res);
};