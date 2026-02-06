/**
 * QAPanel - Unified Q&A Panel (Freeform + Template-driven)
 * 
 * Supports two modes:
 * - Freeform: Users can add any question (when no questionGroup provided)
 * - Template: Questions come from Setting records (when questionGroup provided)
 * 
 * Features:
 * - Predefined answer choices (radio/checkbox in template mode)
 * - Freeform text input
 * - Multi-select support
 * - Image attachments
 * - API integration via qaUtils
 * 
 * Role-based access:
 * - View: All roles (default)
 * - Edit: User+ roles (default)
 */
import React, { useState, useEffect, useCallback, useRef } from 'react';
import { 
  FaQuestionCircle, FaChevronDown, FaChevronUp, FaPlus, 
  FaEdit, FaTrash, FaCheck, FaClock, FaSpinner, FaImage, FaTimes
} from 'react-icons/fa';
import { usePermissions } from './usePermissions';
import type { BasePanelProps, QAEntry } from './types';
import {
  getQAQuestions,
  getQAAnswers,
  saveQAAnswer,
  deleteQAAnswer,
  getEffectiveOptions,
  type QAQuestionsSetting,
  type QAQuestionDef,
  type QAAnswerRecord,
  type QAEffectiveOptions,
} from './qaUtils';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/** Image attachment for Q&A */
interface QAImage {
  id?: string;
  file?: File;
  preview?: string;
  path?: string;
  filename?: string;
  uploaded_at?: string;
}

interface QAPanelProps extends Omit<BasePanelProps<QAEntry[]>, 'data' | 'onChange' | 'entityType' | 'entityId'> {
  /** Q&A entries array (for freeform mode with local state) */
  data?: QAEntry[];
  /** Callback when local data changes (freeform mode) */
  onChange?: (data: QAEntry[]) => void;
  /** Question group name - enables template mode */
  questionGroup?: string;
  /** Parent record type (for API persistence) */
  parentType?: string;
  /** Parent record ID (for API persistence) */
  parentId?: number;
  /** Callback when answers change via API */
  onAnswersChange?: (answers: QAAnswerRecord[]) => void;
  /** Image upload handler */
  onImageUpload?: (file: File) => Promise<{ path: string; filename: string }>;
}

// ---------------------------------------------------------------------------
// Image Upload Component
// ---------------------------------------------------------------------------

interface ImageUploadProps {
  images: QAImage[];
  onChange: (images: QAImage[]) => void;
  maxImages: number;
  acceptTypes: string[];
  disabled?: boolean;
  required?: boolean;
}

const ImageUpload: React.FC<ImageUploadProps> = ({
  images,
  onChange,
  maxImages,
  acceptTypes,
  disabled,
  required,
}) => {
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    if (files.length === 0) return;

    const remaining = maxImages - images.length;
    const toAdd = files.slice(0, remaining).map(file => ({
      id: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
      file,
      preview: URL.createObjectURL(file),
      filename: file.name,
    }));

    onChange([...images, ...toAdd]);
    if (inputRef.current) inputRef.current.value = '';
  };

  const handleRemove = (index: number) => {
    const img = images[index];
    if (img.preview && img.file) {
      URL.revokeObjectURL(img.preview);
    }
    onChange(images.filter((_, i) => i !== index));
  };

  const accept = acceptTypes.map(t => 
    t.startsWith('.') ? t : `.${t}`
  ).join(',');

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2 text-xs text-slate-500">
        <FaImage size={12} />
        <span>
          Images ({images.length}/{maxImages})
          {required && <span className="text-red-500 ml-1">*</span>}
        </span>
      </div>
      
      {/* Image previews */}
      {images.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {images.map((img, index) => (
            <div 
              key={img.id || index} 
              className="relative w-16 h-16 rounded border border-slate-200 dark:border-slate-600 overflow-hidden group"
            >
              <img 
                src={img.preview || img.path} 
                alt={img.filename}
                className="w-full h-full object-cover"
              />
              {!disabled && (
                <button
                  onClick={() => handleRemove(index)}
                  className="absolute top-0 right-0 p-0.5 bg-red-500 text-white rounded-bl opacity-0 group-hover:opacity-100 transition-opacity"
                >
                  <FaTimes size={10} />
                </button>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Add button */}
      {!disabled && images.length < maxImages && (
        <>
          <button
            type="button"
            onClick={() => inputRef.current?.click()}
            className="flex items-center gap-1 px-2 py-1 text-xs text-blue-600 border border-blue-200 rounded hover:bg-blue-50 dark:border-blue-800 dark:hover:bg-blue-900/20"
          >
            <FaPlus size={10} />
            Add Image
          </button>
          <input
            ref={inputRef}
            type="file"
            accept={accept}
            multiple={maxImages - images.length > 1}
            onChange={handleFileSelect}
            className="hidden"
          />
        </>
      )}
    </div>
  );
};

// ---------------------------------------------------------------------------
// Freeform Q&A Item
// ---------------------------------------------------------------------------

interface FreeformQAItemProps {
  entry: QAEntry;
  canEdit: boolean;
  onEdit?: () => void;
  onDelete?: () => void;
  onAnswer?: (answer: string) => void;
  compact?: boolean;
}

const FreeformQAItem: React.FC<FreeformQAItemProps> = ({ 
  entry, 
  canEdit, 
  onEdit, 
  onDelete, 
  onAnswer,
  compact = false 
}) => {
  const [isExpanded, setIsExpanded] = useState(!entry.answer);
  const [answerText, setAnswerText] = useState('');
  const [showAnswerInput, setShowAnswerInput] = useState(false);

  const status = entry.status || (entry.answer ? 'answered' : 'open');
  const statusColor = {
    open: 'text-amber-600 bg-amber-100 dark:bg-amber-900/30',
    answered: 'text-green-600 bg-green-100 dark:bg-green-900/30',
    closed: 'text-slate-500 bg-slate-100 dark:bg-slate-700',
  }[status];

  const handleSubmitAnswer = () => {
    if (answerText.trim() && onAnswer) {
      onAnswer(answerText.trim());
      setAnswerText('');
      setShowAnswerInput(false);
    }
  };

  return (
    <div className={`border rounded-lg border-slate-200 dark:border-slate-600 ${compact ? 'p-2' : 'p-3'}`}>
      {/* Question header */}
      <div 
        className="flex items-start gap-2 cursor-pointer"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <FaQuestionCircle className="text-blue-500 mt-0.5 flex-shrink-0" size={14} />
        <div className="flex-1 min-w-0">
          <p className={`text-sm font-medium text-slate-700 dark:text-slate-300 ${!isExpanded && 'line-clamp-1'}`}>
            {entry.question}
          </p>
          <div className="flex items-center gap-2 mt-1 text-xs text-slate-500">
            <span className={`px-1.5 py-0.5 rounded ${statusColor}`}>
              {status === 'answered' ? <FaCheck size={8} className="inline mr-1" /> : <FaClock size={8} className="inline mr-1" />}
              {status}
            </span>
            {entry.asked_by && <span>by {entry.asked_by}</span>}
            {entry.asked_at && <span>{new Date(entry.asked_at).toLocaleDateString()}</span>}
          </div>
        </div>
        <div className="flex items-center gap-1">
          {canEdit && onEdit && (
            <button
              onClick={(e) => { e.stopPropagation(); onEdit(); }}
              className="p-1 text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded"
            >
              <FaEdit size={12} />
            </button>
          )}
          {canEdit && onDelete && (
            <button
              onClick={(e) => { e.stopPropagation(); onDelete(); }}
              className="p-1 text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded"
            >
              <FaTrash size={12} />
            </button>
          )}
          {isExpanded ? <FaChevronUp size={12} /> : <FaChevronDown size={12} />}
        </div>
      </div>

      {/* Answer section */}
      {isExpanded && (
        <div className="mt-3 ml-6 pl-3 border-l-2 border-green-200 dark:border-green-800">
          {entry.answer ? (
            <div>
              <p className="text-sm text-slate-600 dark:text-slate-400">{entry.answer}</p>
              {(entry.answered_by || entry.answered_at) && (
                <p className="text-xs text-slate-400 mt-1">
                  {entry.answered_by && `Answered by ${entry.answered_by}`}
                  {entry.answered_at && ` on ${new Date(entry.answered_at).toLocaleDateString()}`}
                </p>
              )}
            </div>
          ) : showAnswerInput ? (
            <div className="space-y-2">
              <textarea
                value={answerText}
                onChange={(e) => setAnswerText(e.target.value)}
                placeholder="Type your answer..."
                className="w-full px-2 py-1.5 text-sm border rounded dark:bg-slate-700 dark:border-slate-600"
                rows={2}
                autoFocus
              />
              <div className="flex gap-2">
                <button
                  onClick={handleSubmitAnswer}
                  disabled={!answerText.trim()}
                  className="px-2 py-1 text-xs bg-green-500 text-white rounded hover:bg-green-600 disabled:opacity-50"
                >
                  Submit Answer
                </button>
                <button
                  onClick={() => setShowAnswerInput(false)}
                  className="px-2 py-1 text-xs text-slate-600 hover:bg-slate-100 dark:hover:bg-slate-700 rounded"
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <div className="text-sm text-slate-400 italic">
              No answer yet
              {canEdit && onAnswer && (
                <button
                  onClick={() => setShowAnswerInput(true)}
                  className="ml-2 text-blue-600 hover:underline"
                >
                  Add answer
                </button>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

// ---------------------------------------------------------------------------
// Template Q&A Item
// ---------------------------------------------------------------------------

interface TemplateQAItemProps {
  question: QAQuestionDef;
  options: QAEffectiveOptions;
  existingAnswer?: QAAnswerRecord;
  settingId: number;
  parentType: string;
  parentId: number;
  canEdit: boolean;
  onSave: (answer: QAAnswerRecord) => Promise<void>;
  onImageUpload?: (file: File) => Promise<{ path: string; filename: string }>;
}

const TemplateQAItem: React.FC<TemplateQAItemProps> = ({
  question,
  options,
  existingAnswer,
  settingId,
  parentType,
  parentId,
  canEdit,
  onSave,
  onImageUpload,
}) => {
  const [isExpanded, setIsExpanded] = useState(!existingAnswer?.answer);
  const [selectedChoices, setSelectedChoices] = useState<number[]>(
    existingAnswer?.answers || (existingAnswer?.answer_id ? [existingAnswer.answer_id] : [])
  );
  const [freeformText, setFreeformText] = useState(existingAnswer?.answer || '');
  const [images, setImages] = useState<QAImage[]>(
    existingAnswer?.metadata?.images?.map(img => ({
      path: img.path,
      filename: img.filename,
      uploaded_at: img.uploaded_at,
    })) || []
  );
  const [isSaving, setIsSaving] = useState(false);
  const [isDirty, setIsDirty] = useState(false);

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

  const handleImagesChange = (newImages: QAImage[]) => {
    setImages(newImages);
    setIsDirty(true);
  };

  const handleSave = async () => {
    if (!canEdit || isSaving) return;
    
    setIsSaving(true);
    try {
      // Upload any new images
      const uploadedImages: Array<{ path: string; filename: string; uploaded_at: string }> = [];
      for (const img of images) {
        if (img.file && onImageUpload) {
          const result = await onImageUpload(img.file);
          uploadedImages.push({
            path: result.path,
            filename: result.filename,
            uploaded_at: new Date().toISOString(),
          });
        } else if (img.path) {
          uploadedImages.push({
            path: img.path,
            filename: img.filename || '',
            uploaded_at: img.uploaded_at || new Date().toISOString(),
          });
        }
      }

      const answerRecord: QAAnswerRecord = {
        id: existingAnswer?.id,
        question: question.question,
        setting_id: settingId,
        question_id: question.id,
        parent_type: parentType,
        parent_id: parentId,
        status: 'answered',
        metadata: uploadedImages.length > 0 ? { images: uploadedImages } : undefined,
      };

      if (options.allow_multiple) {
        answerRecord.answers = selectedChoices;
      } else if (selectedChoices.length > 0) {
        answerRecord.answer_id = selectedChoices[0];
        const choice = question.answers?.find(a => a.id === selectedChoices[0]);
        if (choice) {
          answerRecord.answer = choice.answer;
        }
      }

      if (options.allow_freeform && freeformText.trim()) {
        answerRecord.answer = freeformText.trim();
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
            {images.length > 0 && (
              <span className="flex items-center gap-1">
                <FaImage size={10} /> {images.length}
              </span>
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

          {/* Image upload */}
          {(options.require_image || images.length > 0) && (
            <ImageUpload
              images={images}
              onChange={handleImagesChange}
              maxImages={options.image_max}
              acceptTypes={options.image_types}
              disabled={!canEdit}
              required={options.require_image}
            />
          )}
          
          {/* Optional image upload when not required */}
          {canEdit && !options.require_image && images.length === 0 && (
            <button
              type="button"
              onClick={() => setImages([{ id: 'placeholder' }])}
              className="text-xs text-slate-500 hover:text-blue-600 flex items-center gap-1"
            >
              <FaImage size={10} /> Attach images
            </button>
          )}

          {/* Save button */}
          {canEdit && isDirty && (
            <div className="flex justify-end">
              <button
                onClick={handleSave}
                disabled={isSaving || (options.require_image && images.filter(i => i.file || i.path).length === 0)}
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
// Add Question Modal (Freeform mode)
// ---------------------------------------------------------------------------

interface AddQuestionModalProps {
  isOpen: boolean;
  entry?: QAEntry;
  onClose: () => void;
  onSave: (entry: QAEntry) => void;
}

const AddQuestionModal: React.FC<AddQuestionModalProps> = ({ isOpen, entry, onClose, onSave }) => {
  const [question, setQuestion] = useState(entry?.question || '');
  const [answer, setAnswer] = useState(entry?.answer || '');

  useEffect(() => {
    setQuestion(entry?.question || '');
    setAnswer(entry?.answer || '');
  }, [entry, isOpen]);

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave({
      ...entry,
      question,
      answer: answer || undefined,
      asked_at: entry?.asked_at || new Date().toISOString(),
      asked_by: entry?.asked_by || 'current_user',
      status: answer ? 'answered' : 'open',
    });
    onClose();
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-slate-800 rounded-lg p-4 w-96 max-w-full mx-4">
        <h3 className="text-sm font-semibold mb-4 text-slate-700 dark:text-slate-200">
          {entry ? 'Edit Q&A' : 'Add Question'}
        </h3>
        
        <form onSubmit={handleSubmit} className="space-y-3">
          <div>
            <label className="block text-xs text-slate-600 dark:text-slate-400 mb-1">Question</label>
            <textarea
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              className="w-full px-2 py-1.5 text-sm border rounded dark:bg-slate-700 dark:border-slate-600"
              rows={2}
              required
              autoFocus
            />
          </div>

          <div>
            <label className="block text-xs text-slate-600 dark:text-slate-400 mb-1">Answer (optional)</label>
            <textarea
              value={answer}
              onChange={(e) => setAnswer(e.target.value)}
              className="w-full px-2 py-1.5 text-sm border rounded dark:bg-slate-700 dark:border-slate-600"
              rows={2}
            />
          </div>

          <div className="flex justify-end gap-2 mt-4">
            <button
              type="button"
              onClick={onClose}
              className="px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-700 rounded"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-3 py-1.5 text-sm bg-blue-500 text-white rounded hover:bg-blue-600"
            >
              Save
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Main QAPanel Component
// ---------------------------------------------------------------------------

const QAPanel: React.FC<QAPanelProps> = ({
  // Freeform mode props
  data = [],
  onChange,
  // Template mode props
  questionGroup,
  parentType,
  parentId,
  onAnswersChange,
  onImageUpload,
  // Common props
  readOnly = false,
  viewRoles,
  editRoles,
  className = '',
  compact = false,
  title,
  defaultCollapsed = false,
}) => {
  const [isCollapsed, setIsCollapsed] = useState(defaultCollapsed);
  
  // Freeform mode state
  const [showModal, setShowModal] = useState(false);
  const [editingEntry, setEditingEntry] = useState<QAEntry | undefined>();
  const [freeformAnswers, setFreeformAnswers] = useState<QAAnswerRecord[]>([]);
  
  // Template mode state
  const [isLoading, setIsLoading] = useState(false);
  const [setting, setSetting] = useState<QAQuestionsSetting | null>(null);
  const [templateAnswers, setTemplateAnswers] = useState<QAAnswerRecord[]>([]);
  const [error, setError] = useState<string | null>(null);

  // Determine mode
  const isTemplateMode = !!questionGroup;
  const hasApiPersistence = !!(parentType && parentId);
  // Allow freeform questions even in template mode
  const allowFreeform = !isTemplateMode || hasApiPersistence;

  // Check permissions
  const { canView, canEdit: permCanEdit } = usePermissions({
    panelType: 'qa',
    viewRoles,
    editRoles,
    forceReadOnly: readOnly,
  });

  const canEdit = permCanEdit && (hasApiPersistence || !!onChange);

  // Load template data
  useEffect(() => {
    if (!hasApiPersistence && !isTemplateMode) return;

    let mounted = true;

    async function loadData() {
      setIsLoading(true);
      setError(null);

      try {
        const [questionsSetting, existingAnswers] = await Promise.all([
          isTemplateMode ? getQAQuestions(questionGroup!) : Promise.resolve(null),
          hasApiPersistence ? getQAAnswers(parentType!, parentId!) : Promise.resolve([]),
        ]);

        if (!mounted) return;

        if (isTemplateMode && !questionsSetting) {
          setError(`Question group "${questionGroup}" not found`);
          return;
        }

        setSetting(questionsSetting);
        
        // Separate template answers (have question_id) from freeform answers (no question_id or question_id=0)
        const templateQIds = questionsSetting?.data?.questions?.map(q => q.id) || [];
        const templateAns = existingAnswers.filter(a => a.question_id && templateQIds.includes(a.question_id));
        const freeformAns = existingAnswers.filter(a => !a.question_id || !templateQIds.includes(a.question_id));
        
        setTemplateAnswers(templateAns);
        setFreeformAnswers(freeformAns);
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
  }, [questionGroup, parentType, parentId, isTemplateMode, hasApiPersistence]);

  // Template mode: handle save
  const handleSaveTemplateAnswer = useCallback(async (answer: QAAnswerRecord) => {
    const saved = await saveQAAnswer(answer);
    if (saved) {
      setTemplateAnswers(prev => {
        const existing = prev.findIndex(a => a.question_id === answer.question_id);
        if (existing >= 0) {
          const updated = [...prev];
          updated[existing] = saved;
          return updated;
        }
        return [...prev, saved];
      });
      onAnswersChange?.([...templateAnswers, ...freeformAnswers]);
    }
  }, [templateAnswers, freeformAnswers, onAnswersChange]);

  // Freeform: handle save (API mode)
  const handleSaveFreeformAnswer = useCallback(async (entry: QAEntry) => {
    if (!hasApiPersistence) {
      // Local state mode
      if (editingEntry?.id !== undefined) {
        const index = typeof editingEntry.id === 'number' ? editingEntry.id : data.findIndex(e => e.id === editingEntry.id);
        const newData = [...data];
        newData[index] = { ...entry, id: editingEntry.id };
        onChange?.(newData);
      } else {
        onChange?.([...data, { ...entry, id: Date.now() }]);
      }
      return;
    }

    // API mode - save as QAAnswerRecord without question_id
    const answerRecord: QAAnswerRecord = {
      id: editingEntry?.id as number | undefined,
      question: entry.question,
      answer: entry.answer,
      parent_type: parentType!,
      parent_id: parentId!,
      status: entry.answer ? 'answered' : 'open',
      // No question_id means it's a freeform question
    };

    const saved = await saveQAAnswer(answerRecord);
    if (saved) {
      setFreeformAnswers(prev => {
        if (editingEntry?.id) {
          return prev.map(a => a.id === editingEntry.id ? saved : a);
        }
        return [...prev, saved];
      });
      onAnswersChange?.([...templateAnswers, ...freeformAnswers]);
    }
  }, [hasApiPersistence, editingEntry, data, onChange, parentType, parentId, templateAnswers, freeformAnswers, onAnswersChange]);

  const handleAdd = () => {
    setEditingEntry(undefined);
    setShowModal(true);
  };

  const handleEdit = (entry: QAEntry, index: number) => {
    setEditingEntry({ ...entry, id: entry.id || index });
    setShowModal(true);
  };

  const handleDelete = async (index: number) => {
    if (hasApiPersistence) {
      const answer = freeformAnswers[index];
      if (answer?.id) {
        await deleteQAAnswer(answer.id);
        setFreeformAnswers(prev => prev.filter((_, i) => i !== index));
      }
    } else if (onChange) {
      onChange(data.filter((_, i) => i !== index));
    }
  };

  const handleAnswer = (index: number, answer: string) => {
    if (!onChange) return;
    const newData = [...data];
    newData[index] = {
      ...newData[index],
      answer,
      answered_at: new Date().toISOString(),
      answered_by: 'current_user',
      status: 'answered',
    };
    onChange(newData);
  };

  const handleSave = (entry: QAEntry) => {
    handleSaveFreeformAnswer(entry);
  };

  if (!canView) return null;

  // Calculate counts
  const displayTitle = title || (isTemplateMode ? questionGroup : 'Q&A');
  
  const templateCount = setting?.data?.questions?.length || 0;
  const freeformCount = hasApiPersistence ? freeformAnswers.length : data.length;
  const totalCount = templateCount + freeformCount;
  
  const templateAnsweredCount = setting?.data?.questions?.filter(q => 
    templateAnswers.some(a => a.question_id === q.id && a.status === 'answered')
  ).length || 0;
  const freeformAnsweredCount = hasApiPersistence 
    ? freeformAnswers.filter(a => a.status === 'answered' || a.answer).length
    : data.filter(e => e.status === 'answered' || e.answer).length;
  
  const answeredCount = templateAnsweredCount + freeformAnsweredCount;
  const openCount = totalCount - answeredCount;

  return (
    <div className={`bg-white dark:bg-slate-800 rounded-lg border border-indigo-200 dark:border-indigo-800 ${className}`}>
      {/* Header */}
      <div
        className="flex items-center justify-between px-4 py-3 bg-indigo-50 dark:bg-indigo-900/20 border-b border-indigo-200 dark:border-indigo-800 cursor-pointer rounded-t-lg"
        onClick={() => setIsCollapsed(!isCollapsed)}
      >
        <div className="flex items-center gap-2">
          <FaQuestionCircle className="text-indigo-500" size={14} />
          <h3 className="text-sm font-semibold text-indigo-700 dark:text-indigo-300">{displayTitle}</h3>
          {totalCount > 0 && (
            <span className="px-1.5 py-0.5 text-xs bg-indigo-100 dark:bg-indigo-900 text-indigo-600 dark:text-indigo-300 rounded-full">
              {answeredCount}/{totalCount}
            </span>
          )}
          {openCount > 0 && (
            <span className="px-1.5 py-0.5 text-xs bg-amber-100 dark:bg-amber-900 text-amber-700 dark:text-amber-300 rounded">
              {openCount} open
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {allowFreeform && canEdit && !isCollapsed && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                handleAdd();
              }}
              className="p-1 text-indigo-600 hover:bg-indigo-100 dark:hover:bg-indigo-800 rounded"
              title="Add question"
            >
              <FaPlus size={12} />
            </button>
          )}
          {isCollapsed ? <FaChevronDown size={12} /> : <FaChevronUp size={12} />}
        </div>
      </div>

      {/* Content */}
      {!isCollapsed && (
        <div className={`${compact ? 'p-2' : 'p-4'} space-y-2`}>
          {isLoading ? (
            <div className="flex items-center justify-center py-8 text-slate-400">
              <FaSpinner className="animate-spin mr-2" />
              Loading questions...
            </div>
          ) : error ? (
            <div className="text-center py-4 text-red-500 text-sm">
              {error}
            </div>
          ) : (
            <>
              {/* Template questions */}
              {isTemplateMode && setting && setting.data?.questions && setting.data.questions.length > 0 && (
                <>
                  {setting.data.questions.map(question => {
                    const options = getEffectiveOptions(question, setting.data.template);
                    const existingAnswer = templateAnswers.find(a => a.question_id === question.id);
                    
                    return (
                      <TemplateQAItem
                        key={question.id}
                        question={question}
                        options={options}
                        existingAnswer={existingAnswer}
                        settingId={setting.id}
                        parentType={parentType!}
                        parentId={parentId!}
                        canEdit={canEdit}
                        onSave={handleSaveTemplateAnswer}
                        onImageUpload={onImageUpload}
                      />
                    );
                  })}
                </>
              )}

              {/* Divider between template and freeform */}
              {isTemplateMode && setting && setting.data?.questions && setting.data.questions.length > 0 && freeformCount > 0 && (
                <div className="border-t border-slate-200 dark:border-slate-700 my-3 pt-2">
                  <span className="text-xs text-slate-400 font-medium">Additional Questions</span>
                </div>
              )}

              {/* Freeform questions */}
              {hasApiPersistence ? (
                // API-persisted freeform answers
                freeformAnswers.length > 0 && freeformAnswers.map((answer, index) => (
                  <FreeformQAItem
                    key={answer.id || index}
                    entry={{
                      id: answer.id,
                      question: answer.question || '',
                      answer: answer.answer,
                      status: answer.status,
                      answered_at: answer.updated_at,
                      answered_by: answer.answered_by?.attention || String(answer.answered_by?.id),
                    }}
                    canEdit={canEdit}
                    compact={compact}
                    onEdit={() => handleEdit({ 
                      id: answer.id, 
                      question: answer.question || '', 
                      answer: answer.answer,
                      status: answer.status,
                    }, index)}
                    onDelete={() => handleDelete(index)}
                  />
                ))
              ) : (
                // Local state freeform entries
                data.map((entry, index) => (
                  <FreeformQAItem
                    key={entry.id || index}
                    entry={entry}
                    canEdit={canEdit}
                    compact={compact}
                    onEdit={() => handleEdit(entry, index)}
                    onDelete={() => handleDelete(index)}
                    onAnswer={canEdit ? (answer) => handleAnswer(index, answer) : undefined}
                  />
                ))
              )}

              {/* Empty state */}
              {totalCount === 0 && (
                <div className="text-center py-4 text-slate-400 text-sm">
                  <FaQuestionCircle size={24} className="mx-auto mb-2 opacity-50" />
                  <p>No questions yet</p>
                  {canEdit && allowFreeform && (
                    <button
                      onClick={handleAdd}
                      className="mt-2 text-indigo-600 hover:underline text-xs"
                    >
                      + Add first question
                    </button>
                  )}
                </div>
              )}

              {/* Add button when there are template questions but no freeform yet */}
              {isTemplateMode && canEdit && freeformCount === 0 && totalCount > 0 && (
                <button
                  onClick={handleAdd}
                  className="w-full mt-2 py-2 text-xs text-indigo-600 hover:bg-indigo-50 dark:hover:bg-indigo-900/20 rounded border border-dashed border-indigo-300 dark:border-indigo-700"
                >
                  + Add custom question
                </button>
              )}
            </>
          )}
        </div>
      )}

      {/* Modal for adding/editing freeform questions */}
      {allowFreeform && (
        <AddQuestionModal
          isOpen={showModal}
          entry={editingEntry}
          onClose={() => setShowModal(false)}
          onSave={handleSave}
        />
      )}
    </div>
  );
};

export default QAPanel;
