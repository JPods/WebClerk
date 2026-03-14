/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import { getRecords, saveRecord, deleteRecord } from "@/api/wcapi";
import type {
  CreateQuestionAnswerRequest,
  QuestionAnswerApiTask,
  UpdateQuestionAnswerRequest,
} from "../types/questionAnswerType";

export const createQuestionAnswer = async (
  payload: CreateQuestionAnswerRequest
): Promise<QuestionAnswerApiTask> => {
  const res = await saveRecord("question_answer", payload);
  return res;
};

export const updateQuestionAnswer = async (
  payload: UpdateQuestionAnswerRequest
): Promise<QuestionAnswerApiTask> => {
  const res = await saveRecord("question_answer", payload);
  return res;
};

export const deleteQuestionAnswer = async (id: number) => {
  return deleteRecord("question_answer", id);
};

export const fetchQuestionAnswers = async (params?: any) => {
  const res = await getRecords("question_answer", params);
  return { status: 200, data: { items: res.results || [] } };
};

export const fetchQuestionAnswer = async (): Promise<QuestionAnswerApiTask[]> => {
  const res = await getRecords("question_answer");
  return res.results || [];
};