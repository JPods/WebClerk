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
 * Fetch all Q&A question groups, optionally filtered by model_target
 */
export async function getAllQAQuestionGroups(modelTarget?: string): Promise<QAQuestionsSetting[]> {
  try {
    const params: Record<string, string> = {
      model_name: 'setting',
      purpose: 'qa_questions',
    };
    if (modelTarget) {
      params.model_target = modelTarget;
    }
    const res = await apiClient.get<ApiEnvelope<GetListPayload>>('/wcapi/get/', { params });
    return res.data.data.results || [];
  } catch (err: any) {
    console.error('Failed to fetch Q&A question groups:', err);
    return [];
  }
}

/** Scoped question groups organized by level */
export interface ScopedQAGroups {
  global: QAQuestionsSetting[];        // model_target is null/empty
  appLevel: QAQuestionsSetting[];      // model_target matches the app (e.g., "transactions")
  modelSpecific: QAQuestionsSetting[]; // model_target matches the specific model
  all: QAQuestionsSetting[];           // combined list (model > app > global priority)
}

/**
 * App registry - maps app names to their models
 * Used for app-level QA question scoping
 */
export const APP_MODEL_REGISTRY: Record<string, string[]> = {
  transactions: ['order', 'purchase', 'workorder', 'invoice', 'estimate', 'quote', 'receipt', 'payment'],
  contacts: ['customer', 'vendor', 'contact', 'employee', 'company'],
  inventory: ['item', 'inventory', 'location', 'warehouse', 'bin'],
  projects: ['project', 'task', 'milestone'],
  accounting: ['journal', 'gl_account', 'ledger', 'tax'],
};

/**
 * Get the app name for a given model
 */
export function getAppForModel(modelName: string): string | null {
  for (const [appName, models] of Object.entries(APP_MODEL_REGISTRY)) {
    if (models.includes(modelName)) {
      return appName;
    }
  }
  return null;
}

/**
 * Check if a model_target value is an app name
 */
export function isAppName(target: string): boolean {
  return target in APP_MODEL_REGISTRY;
}

/**
 * Fetch Q&A question groups scoped for a specific model
 * Returns groups organized by scope level:
 * - global: applies to all models (model_target is null)
 * - appLevel: applies to all models in the same app (e.g., all transactions)
 * - modelSpecific: applies only to this model
 */
export async function getScopedQAQuestionGroups(modelName?: string): Promise<ScopedQAGroups> {
  try {
    // Fetch all groups in one call
    const allGroups = await getAllQAQuestionGroups();
    
    const global: QAQuestionsSetting[] = [];
    const appLevel: QAQuestionsSetting[] = [];
    const modelSpecific: QAQuestionsSetting[] = [];
    
    const appName = modelName ? getAppForModel(modelName) : null;
    
    for (const group of allGroups) {
      if (!group.model_target) {
        // No model_target = global
        global.push(group);
      } else if (isAppName(group.model_target)) {
        // Target is an app name
        if (appName && group.model_target === appName) {
          // Matches the model's app
          appLevel.push(group);
        }
      } else if (modelName && group.model_target === modelName) {
        // Matches specific model
        modelSpecific.push(group);
      }
      // Groups with model_target that don't match are excluded
    }
    
    return {
      global,
      appLevel,
      modelSpecific,
      // Combined: model-specific first, then app-level, then global
      all: [...modelSpecific, ...appLevel, ...global],
    };
  } catch (err: any) {
    console.error('Failed to fetch scoped Q&A question groups:', err);
    return { global: [], appLevel: [], modelSpecific: [], all: [] };
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