/**
 * Q&A API utilities and types
 * 
 * Fetches question templates from Setting records and manages Q&A answers.
 * See: readmes/topics/settings-api.md
 */
import { apiClient } from '@/api/axios';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/** Template defaults for a question group */
export interface QAQuestionTemplate {
  allow_freeform?: boolean;
  allow_multiple?: boolean;
  require_image?: boolean;
  image_max?: number;
  image_types?: string[];
}

/** Answer choice within a question */
export interface QAAnswerChoice {
  id: number;
  answer: string;
}

/** Question definition from Setting */
export interface QAQuestionDef {
  id: number;
  question: string;
  answers?: QAAnswerChoice[];
  // Question-level overrides
  allow_freeform?: boolean;
  allow_multiple?: boolean;
  require_image?: boolean;
}

/** Full Q&A questions data from Setting.data */
export interface QAQuestionsData {
  template: QAQuestionTemplate;
  questions: QAQuestionDef[];
}

/** Setting record for qa_questions */
export interface QAQuestionsSetting {
  id: number;
  purpose: string;
  name: string;
  model_target?: string;
  role?: string;
  data: QAQuestionsData;
}

/** Counters singleton data */
export interface QACountersData {
  question_max: number;
  answer_max: number;
}

/** Resolved effective options for a question */
export interface QAEffectiveOptions {
  allow_freeform: boolean;
  allow_multiple: boolean;
  require_image: boolean;
  image_max: number;
  image_types: string[];
}

/** Answer record (saved to QuestionAnswer model) */
export interface QAAnswerRecord {
  id?: number;
  question: string;
  answer?: string;            // For freeform or single select
  answers?: number[];         // For multiple select (array of answer_ids)
  setting_id?: number;        // FK to Setting (question template)
  question_id?: number;       // ID of question within Setting
  answer_id?: number;         // ID of selected answer (single select)
  parent_type: string;
  parent_id: number;
  status?: 'open' | 'answered' | 'closed';
  sequence?: number;
  metadata?: {
    images?: Array<{
      path: string;
      filename: string;
      uploaded_at: string;
      uploaded_by?: number;
    }>;
  };
  answered_by?: { id: number; attention?: string };
  created_at?: string;
  updated_at?: string;
}

// ---------------------------------------------------------------------------
// Defaults
// ---------------------------------------------------------------------------

const DEFAULTS: Required<QAQuestionTemplate> = {
  allow_freeform: false,
  allow_multiple: false,
  require_image: false,
  image_max: 5,
  image_types: ['jpg', 'png', 'webp', 'pdf'],
};

// ---------------------------------------------------------------------------
// Helper Functions
// ---------------------------------------------------------------------------

/**
 * Resolve effective options for a question
 * Priority: question.option ?? template.option ?? default
 */
export function getEffectiveOptions(
  question: QAQuestionDef,
  template: QAQuestionTemplate
): QAEffectiveOptions {
  return {
    allow_freeform: question.allow_freeform ?? template.allow_freeform ?? DEFAULTS.allow_freeform,
    allow_multiple: question.allow_multiple ?? template.allow_multiple ?? DEFAULTS.allow_multiple,
    require_image: question.require_image ?? template.require_image ?? DEFAULTS.require_image,
    image_max: template.image_max ?? DEFAULTS.image_max,
    image_types: template.image_types ?? DEFAULTS.image_types,
  };
}

// ---------------------------------------------------------------------------
// API Functions
// ---------------------------------------------------------------------------

interface ApiEnvelope<T> {
  data: T;
  status?: string;
}

interface GetListPayload {
  results: any[];
  count?: number;
}

/**
 * Fetch Q&A counters singleton
 */
export async function getQACounters(): Promise<QACountersData | null> {
  try {
    const res = await apiClient.get<ApiEnvelope<GetListPayload>>('/wcapi/get/', {
      params: {
        model_name: 'setting',
        purpose: 'qa_counters',
      },
    });
    const results = res.data.data.results || [];
    return results.length > 0 ? results[0].data : null;
  } catch (err: any) {
    console.error('Failed to fetch Q&A counters:', err);
    return null;
  }
}

/**
 * Fetch Q&A questions for a specific group
 */
export async function getQAQuestions(groupName: string): Promise<QAQuestionsSetting | null> {
  try {
    const res = await apiClient.get<ApiEnvelope<GetListPayload>>('/wcapi/get/', {
      params: {
        model_name: 'setting',
        purpose: 'qa_questions',
        name: groupName,
      },
    });
    const results = res.data.data.results || [];
    return results.length > 0 ? results[0] : null;
  } catch (err: any) {
    console.error(`Failed to fetch Q&A questions for ${groupName}:`, err);
    return null;
  }
}

/**
 * Fetch all Q&A question groups
 */
export async function getAllQAQuestionGroups(): Promise<QAQuestionsSetting[]> {
  try {
    const res = await apiClient.get<ApiEnvelope<GetListPayload>>('/wcapi/get/', {
      params: {
        model_name: 'setting',
        purpose: 'qa_questions',
      },
    });
    return res.data.data.results || [];
  } catch (err: any) {
    console.error('Failed to fetch Q&A question groups:', err);
    return [];
  }
}

/**
 * Fetch answers for a parent record
 */
export async function getQAAnswers(
  parentType: string,
  parentId: number
): Promise<QAAnswerRecord[]> {
  try {
    const res = await apiClient.get<ApiEnvelope<GetListPayload>>('/wcapi/get/', {
      params: {
        model_name: 'question_answer',
        parent_type: parentType,
        parent_id: parentId,
      },
    });
    return res.data.data.results || [];
  } catch (err: any) {
    console.error(`Failed to fetch Q&A answers for ${parentType}/${parentId}:`, err);
    return [];
  }
}

/**
 * Save a Q&A answer
 */
export async function saveQAAnswer(answer: QAAnswerRecord): Promise<QAAnswerRecord | null> {
  try {
    const res = await apiClient.post<ApiEnvelope<any>>('/wcapi/save/', {
      model_name: 'question_answer',
      ...answer,
    });
    return res.data.data;
  } catch (err: any) {
    console.error('Failed to save Q&A answer:', err);
    throw err;
  }
}

/**
 * Delete a Q&A answer
 */
export async function deleteQAAnswer(id: number): Promise<boolean> {
  try {
    await apiClient.post('/wcapi/delete/', {
      model_name: 'question_answer',
      id,
    });
    return true;
  } catch (err: any) {
    console.error('Failed to delete Q&A answer:', err);
    return false;
  }
}

/**
 * Upload image for Q&A answer
 * 
 * @deprecated Use uploadDocument from './documentUpload' for full Document record tracking.
 * This function is kept for backward compatibility but will upload without creating
 * a Document record. Prefer using uploadDocument with purpose='qa_image'.
 */
export async function uploadQAImage(
  file: File,
  parentType: string,
  parentId: number
): Promise<{ path: string; filename: string }> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('parent_type', parentType);
  formData.append('parent_id', String(parentId));
  formData.append('purpose', 'qa_image');

  const res = await apiClient.post<{ data: { path: string; filename: string } }>(
    '/wcapi/upload/',
    formData,
    {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    }
  );

  return res.data.data;
}