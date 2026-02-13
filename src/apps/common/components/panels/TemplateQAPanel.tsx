/**
 * TemplateQAPanel - Template-driven Q&A Panel
 * 
 * Fetches question templates from Setting records and renders them
 * with predefined answer choices, freeform input, and multi-select support.
 * 
 * See: readmes/topics/qa/qa_implementation_plan.md
 */
import React, { useState, useEffect, useCallback, useRef } from 'react';
import { 
  FaQuestionCircle, FaChevronDown, FaChevronUp, 
  FaCheck, FaClock, FaSpinner, FaCamera, FaTimes, FaImage
} from 'react-icons/fa';
import { uploadDocument } from './documentUpload';
import { usePermissions } from './usePermissions';
import type { BasePanelProps } from './types';
import {
  getQAQuestions,
  getQAAnswers,
  saveQAAnswer,
  getEffectiveOptions,
  type QAQuestionsSetting,
  type QAQuestionDef,
  type QAAnswerRecord,
  type QAEffectiveOptions,
} from './qaUtils';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface TemplateQAPanelProps extends Omit<BasePanelProps<unknown>, 'data' | 'onChange' | 'entityType' | 'entityId'> {
  /** Question group name (e.g., "Planning", "Prepress") */
  questionGroup: string;
  /** Parent record type (e.g., "sales_order", "project") */
  parent_model: string;
  /** Parent record ID */
  parentId: number;
  /** Callback when answers change */
  onAnswersChange?: (answers: QAAnswerRecord[]) => void;
}

// ---------------------------------------------------------------------------
// Question Item Component
// ---------------------------------------------------------------------------

interface QuestionItemProps {
  question: QAQuestionDef;
  options: QAEffectiveOptions;
  existingAnswer?: QAAnswerRecord;
  settingId: number;
  parent_model: string;
  parentId: number;
  canEdit: boolean;
  onSave: (answer: QAAnswerRecord) => Promise<void>;
}

interface QAImageInfo {
  path: string;
  filename: string;
  uploaded_at: string;
  uploaded_by?: number;
  document_id?: number;
}

const QuestionItem: React.FC<QuestionItemProps> = ({
  question,
  options,
  existingAnswer,
  settingId,
  parent_model,
  parentId,
  canEdit,
  onSave,
}) => {
  const [isExpanded, setIsExpanded] = useState(!existingAnswer?.answer);
  const [selectedChoices, setSelectedChoices] = useState<number[]>(
    existingAnswer?.answers || (existingAnswer?.answer_id ? [existingAnswer.answer_id] : [])
  );
  const [freeformText, setFreeformText] = useState(existingAnswer?.answer || '');
  const [isSaving, setIsSaving] = useState(false);
  const [isDirty, setIsDirty] = useState(false);
  const [images, setImages] = useState<QAImageInfo[]>(existingAnswer?.metadata?.images || []);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const hasAnswer = existingAnswer?.answer || (existingAnswer?.answers?.length ?? 0) > 0 || existingAnswer?.answer_id;
  const status = existingAnswer?.status || (hasAnswer ? 'answered' : 'open');
  
  const statusColor = {
    open: 'text-amber-600 bg-amber-100 dark:bg-amber-900/30',
    answered: 'text-green-600 bg-green-100 dark:bg-green-900/30',
    closed: 'text-slate-500 bg-slate-100 dark:bg-slate-700',
  }[status];

  const handleChoiceToggle = (choiceId: number) => {
    if (!canEdit) return;
    
    if (options.allow_multiple) {
      setSelectedChoices(prev => 
        prev.includes(choiceId) 
          ? prev.filter(id => id !== choiceId)
          : [...prev, choiceId]
      );
    } else {
      setSelectedChoices([choiceId]);
    }
    setIsDirty(true);
  };

  const handleFreeformChange = (text: string) => {
    setFreeformText(text);
    setIsDirty(true);
  };

  const handleImageUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0 || !canEdit) return;

    // Check max images
    if (images.length >= options.image_max) {
      setUploadError(`Maximum ${options.image_max} images allowed`);
      return;
    }

    const file = files[0];
    
    // Validate extension
    const ext = file.name.split('.').pop()?.toLowerCase();
    if (!ext || !options.image_types.includes(ext)) {
      setUploadError(`File type not allowed. Allowed: ${options.image_types.join(', ')}`);
      return;
    }

    setIsUploading(true);
    setUploadError(null);

    try {
      const result = await uploadDocument({
        file,
        parent_model,
        parentId,
        purpose: 'qa_image',
        description: `QA: ${question.question}`,
      });

      const newImage: QAImageInfo = {
        path: result.url || result.document.path?.url || '',
        filename: result.document.name,
        uploaded_at: new Date().toISOString(),
        document_id: result.document.id,
      };

      setImages(prev => [...prev, newImage]);
      setIsDirty(true);
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setIsUploading(false);
      // Reset file input
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleRemoveImage = (index: number) => {
    if (!canEdit) return;
    setImages(prev => prev.filter((_, i) => i !== index));
    setIsDirty(true);
  };

  const handleSave = async () => {
    if (!canEdit || isSaving) return;
    
    setIsSaving(true);
    try {
      const answerRecord: QAAnswerRecord = {
        id: existingAnswer?.id,
        question: question.question,
        setting_id: settingId,
        question_id: question.id,
        parent_model: parent_model,
        parent_id: parentId,
        status: 'answered',
      };

      if (options.allow_multiple) {
        answerRecord.answers = selectedChoices;
      } else if (selectedChoices.length > 0) {
        answerRecord.answer_id = selectedChoices[0];
        // Also store the text value
        const choice = question.answers?.find(a => a.id === selectedChoices[0]);
        if (choice) {
          answerRecord.answer = choice.answer;
        }
      }

      if (options.allow_freeform && freeformText.trim()) {
        answerRecord.answer = freeformText.trim();
      }

      // Add images to metadata
      if (images.length > 0) {
        answerRecord.metadata = {
          ...answerRecord.metadata,
          images,
        };
      }

      await onSave(answerRecord);
      setIsDirty(false);
    } finally {
      setIsSaving(false);
    }
  };

  // Get display text for current answer
  const getAnswerDisplay = () => {
    if (options.allow_freeform && freeformText) {
      return freeformText;
    }
    if (selectedChoices.length > 0 && question.answers) {
      const selected = question.answers.filter(a => selectedChoices.includes(a.id));
      return selected.map(a => a.answer).join(', ');
    }
    return null;
  };

  const answerDisplay = getAnswerDisplay();

  return (
    <div className="border rounded-lg border-slate-200 dark:border-slate-600 p-3">
      {/* Question header */}
      <div 
        className="flex items-start gap-2 cursor-pointer"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <FaQuestionCircle className="text-blue-500 mt-0.5 flex-shrink-0" size={14} />
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-slate-700 dark:text-slate-300">
            {question.question}
            {options.require_image && <span className="text-red-500 ml-1">*</span>}
          </p>
          <div className="flex items-center gap-2 mt-1 text-xs text-slate-500">
            <span className={`px-1.5 py-0.5 rounded ${statusColor}`}>
              {status === 'answered' ? <FaCheck size={8} className="inline mr-1" /> : <FaClock size={8} className="inline mr-1" />}
              {status}
            </span>
            {!isExpanded && answerDisplay && (
              <span className="truncate max-w-[200px]">{answerDisplay}</span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-1">
          {isExpanded ? <FaChevronUp size={12} /> : <FaChevronDown size={12} />}
        </div>
      </div>

      {/* Answer section */}
      {isExpanded && (
        <div className="mt-3 ml-6 space-y-3">
          {/* Predefined choices */}
          {question.answers && question.answers.length > 0 && (
            <div className="space-y-1">
              {question.answers.map(choice => (
                <label 
                  key={choice.id}
                  className={`flex items-center gap-2 p-2 rounded cursor-pointer transition-colors ${
                    selectedChoices.includes(choice.id)
                      ? 'bg-blue-50 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-700'
                      : 'hover:bg-slate-50 dark:hover:bg-slate-700/50 border border-transparent'
                  } ${!canEdit ? 'cursor-default' : ''}`}
                >
                  <input
                    type={options.allow_multiple ? 'checkbox' : 'radio'}
                    name={`q_${question.id}`}
                    checked={selectedChoices.includes(choice.id)}
                    onChange={() => handleChoiceToggle(choice.id)}
                    disabled={!canEdit}
                    className="text-blue-600"
                  />
                  <span className="text-sm text-slate-700 dark:text-slate-300">
                    {choice.answer}
                  </span>
                </label>
              ))}
            </div>
          )}

          {/* Freeform input */}
          {options.allow_freeform && (
            <div>
              <textarea
                value={freeformText}
                onChange={(e) => handleFreeformChange(e.target.value)}
                placeholder={question.answers?.length ? 'Or enter custom answer...' : 'Enter your answer...'}
                className="w-full px-2 py-1.5 text-sm border rounded dark:bg-slate-700 dark:border-slate-600 focus:ring-1 focus:ring-blue-500"
                rows={2}
                disabled={!canEdit}
              />
            </div>
          )}

          {/* Image upload section */}
          {(options.require_image || images.length > 0) && (
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-xs text-slate-600 dark:text-slate-400">
                <FaImage size={12} />
                <span>
                  {options.require_image ? 'Image required' : 'Images'}
                  {images.length > 0 && ` (${images.length}/${options.image_max})`}
                </span>
              </div>

              {/* Image thumbnails */}
              {images.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {images.map((img, idx) => (
                    <div key={idx} className="relative group">
                      <img
                        src={img.path}
                        alt={img.filename}
                        className="w-16 h-16 object-cover rounded border dark:border-slate-600"
                      />
                      {canEdit && (
                        <button
                          onClick={() => handleRemoveImage(idx)}
                          className="absolute -top-1 -right-1 w-4 h-4 bg-red-500 text-white rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                        >
                          <FaTimes size={8} />
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              )}

              {/* Upload button */}
              {canEdit && images.length < options.image_max && (
                <div>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept={options.image_types.map(t => `.${t}`).join(',')}
                    onChange={handleImageUpload}
                    className="hidden"
                    disabled={isUploading}
                  />
                  <button
                    onClick={() => fileInputRef.current?.click()}
                    disabled={isUploading}
                    className="flex items-center gap-1.5 px-2 py-1 text-xs border rounded hover:bg-slate-50 dark:hover:bg-slate-700 disabled:opacity-50"
                  >
                    {isUploading ? (
                      <FaSpinner className="animate-spin" size={10} />
                    ) : (
                      <FaCamera size={10} />
                    )}
                    {isUploading ? 'Uploading...' : 'Add Image'}
                  </button>
                </div>
              )}

              {/* Error message */}
              {uploadError && (
                <p className="text-xs text-red-500">{uploadError}</p>
              )}
            </div>
          )}

          {/* Save button */}
          {canEdit && isDirty && (
            <div className="flex justify-end">
              <button
                onClick={handleSave}
                disabled={isSaving}
                className="px-3 py-1.5 text-xs bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50 flex items-center gap-1"
              >
                {isSaving && <FaSpinner className="animate-spin" size={10} />}
                Save Answer
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

// ---------------------------------------------------------------------------
// Main Template QA Panel
// ---------------------------------------------------------------------------

const TemplateQAPanel: React.FC<TemplateQAPanelProps> = ({
  questionGroup,
  parent_model,
  parentId,
  readOnly = false,
  viewRoles,
  editRoles,
  className = '',
  compact: _compact = false,
  title,
  defaultCollapsed = false,
  onAnswersChange,
}) => {
  const [isCollapsed, setIsCollapsed] = useState(defaultCollapsed);
  const [isLoading, setIsLoading] = useState(true);
  const [setting, setSetting] = useState<QAQuestionsSetting | null>(null);
  const [answers, setAnswers] = useState<QAAnswerRecord[]>([]);
  const [error, setError] = useState<string | null>(null);

  // Check permissions
  const { canView, canEdit: permCanEdit } = usePermissions({
    panelType: 'qa',
    viewRoles,
    editRoles,
    forceReadOnly: readOnly,
  });

  const canEdit = permCanEdit && !readOnly;

  // Load data
  useEffect(() => {
    let mounted = true;

    async function loadData() {
      setIsLoading(true);
      setError(null);

      try {
        const [questionsSetting, existingAnswers] = await Promise.all([
          getQAQuestions(questionGroup),
          parentId ? getQAAnswers(parent_model, parentId) : Promise.resolve([]),
        ]);

        if (!mounted) return;

        if (!questionsSetting) {
          setError(`Question group "${questionGroup}" not found`);
          return;
        }

        setSetting(questionsSetting);
        setAnswers(existingAnswers);
      } catch (err) {
        if (!mounted) return;
        setError('Failed to load Q&A data');
        console.error(err);
      } finally {
        if (mounted) {
          setIsLoading(false);
        }
      }
    }

    loadData();

    return () => {
      mounted = false;
    };
  }, [questionGroup, parent_model, parentId]);

  // Handle save
  const handleSaveAnswer = useCallback(async (answer: QAAnswerRecord) => {
    const saved = await saveQAAnswer(answer);
    if (saved) {
      setAnswers(prev => {
        const existing = prev.findIndex(a => a.question_id === answer.question_id);
        if (existing >= 0) {
          const updated = [...prev];
          updated[existing] = saved;
          return updated;
        }
        return [...prev, saved];
      });
      onAnswersChange?.(answers);
    }
  }, [answers, onAnswersChange]);

  if (!canView) return null;

  // Count answered questions
  const answeredCount = setting?.data?.questions?.filter(q => 
    answers.some(a => a.question_id === q.id && a.status === 'answered')
  ).length || 0;
  const totalCount = setting?.data?.questions?.length || 0;

  const displayTitle = title || questionGroup;

  return (
    <div className={`bg-white dark:bg-slate-800 rounded-lg border border-indigo-200 dark:border-indigo-800 ${className}`}>
      {/* Header */}
      <div
        className="flex items-center justify-between px-4 py-3 bg-indigo-50 dark:bg-indigo-900/20 border-b border-indigo-200 dark:border-indigo-800 cursor-pointer rounded-t-lg"
        onClick={() => setIsCollapsed(!isCollapsed)}
      >
        <div className="flex items-center gap-2">
          <FaQuestionCircle className="text-indigo-500" size={14} />
          <h3 className="text-sm font-semibold text-indigo-700 dark:text-indigo-300">
            {displayTitle}
          </h3>
          {totalCount > 0 && (
            <span className="px-1.5 py-0.5 text-xs bg-indigo-100 dark:bg-indigo-900 text-indigo-600 dark:text-indigo-300 rounded-full">
              {answeredCount}/{totalCount}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {isCollapsed ? <FaChevronDown size={12} /> : <FaChevronUp size={12} />}
        </div>
      </div>

      {/* Content */}
      {!isCollapsed && (
        <div className="p-4 space-y-3">
          {isLoading ? (
            <div className="flex items-center justify-center py-8 text-slate-400">
              <FaSpinner className="animate-spin mr-2" />
              Loading questions...
            </div>
          ) : error ? (
            <div className="text-center py-4 text-red-500 text-sm">
              {error}
            </div>
          ) : !setting?.data?.questions?.length ? (
            <div className="text-center py-4 text-slate-400 text-sm">
              <FaQuestionCircle size={24} className="mx-auto mb-2 opacity-50" />
              <p>No questions in this group</p>
            </div>
          ) : (
            setting.data.questions.map(question => {
              const options = getEffectiveOptions(question, setting.data.template);
              const existingAnswer = answers.find(a => a.question_id === question.id);
              
              return (
                <QuestionItem
                  key={question.id}
                  question={question}
                  options={options}
                  existingAnswer={existingAnswer}
                  settingId={setting.id}
                  parent_model={parent_model}
                  parentId={parentId}
                  canEdit={canEdit}
                  onSave={handleSaveAnswer}
                />
              );
            })
          )}
        </div>
      )}
    </div>
  );
};

export default TemplateQAPanel;
