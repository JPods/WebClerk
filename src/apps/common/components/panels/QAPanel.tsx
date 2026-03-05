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
  FaEdit, FaTrash, FaCheck, FaClock, FaSpinner, FaImage, FaTimes,
  FaExclamationTriangle
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
import { withDevIdentifier } from '@/components/common/DevIdentifier';

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
  /** Parent record model name (for API persistence, e.g., 'order', 'customer') */
  parent_model?: string;
  /** Parent record ID (for API persistence) */
  parentId?: number;
  /** Callback when answers change via API */
  onAnswersChange?: (answers: QAAnswerRecord[]) => void;
  /** Callback to update refs.links.question_answer on parent record */
  onLinksChange?: (links: Array<{ id: number }>) => void;
  /** Image upload handler */
  onImageUpload?: (file: File) => Promise<{ path: string; filename: string }>;
}

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
    <div className={`border rounded-lg border-slate-200 dark:border-slate-600 ${compact ? 'p-1.5' : 'p-2'}`}>
      {/* Question row - horizontal layout */}
      <div 
        className="flex items-center gap-1.5 cursor-pointer flex-wrap"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <FaQuestionCircle className="text-blue-500 flex-shrink-0" size={11} />
        <span className="text-xs font-medium text-slate-700 dark:text-slate-300">
          {entry.question}
        </span>
        {entry.answer && !isExpanded && (
          <>
            <span className="text-slate-400">→</span>
            <span className="text-xs text-green-600 dark:text-green-400 truncate max-w-[200px]">
              {entry.answer}
            </span>
          </>
        )}
        <span className={`px-1 py-0.5 rounded text-[10px] ${statusColor}`}>
          {status === 'answered' ? <FaCheck size={7} className="inline" /> : <FaClock size={7} className="inline" />}
        </span>
        <div className="ml-auto flex items-center gap-1">
          {canEdit && onEdit && (
            <button
              onClick={(e) => { e.stopPropagation(); onEdit(); }}
              className="p-0.5 text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded"
            >
              <FaEdit size={10} />
            </button>
          )}
          {canEdit && onDelete && (
            <button
              onClick={(e) => { e.stopPropagation(); onDelete(); }}
              className="p-0.5 text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded"
            >
              <FaTrash size={10} />
            </button>
          )}
          {isExpanded ? <FaChevronUp size={10} /> : <FaChevronDown size={10} />}
        </div>
      </div>

      {/* Answer section */}
      {isExpanded && (
        <div className="mt-1.5 ml-4 pl-2 border-l-2 border-green-200 dark:border-green-800">
          {entry.answer ? (
            <div>
              <p className="text-xs text-slate-600 dark:text-slate-400">{entry.answer}</p>
              {(entry.answered_by || entry.answered_at) && (
                <p className="text-[10px] text-slate-400 mt-0.5">
                  {entry.answered_by && `by ${entry.answered_by}`}
                  {entry.answered_at && ` · ${new Date(entry.answered_at).toLocaleDateString()}`}
                </p>
              )}
            </div>
          ) : showAnswerInput ? (
            <div className="space-y-1.5">
              <textarea
                value={answerText}
                onChange={(e) => setAnswerText(e.target.value)}
                placeholder="Type your answer..."
                className="w-full px-2 py-1 text-xs border rounded dark:bg-slate-700 dark:border-slate-600"
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
  parent_model: string;
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
  parent_model,
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

  const handleChoiceToggle = async (choiceId: number) => {
    if (!canEdit || isSaving) return;
    
    if (options.allow_multiple) {
      // For multiple select, toggle immediately and mark dirty
      setSelectedChoices(prev => 
        prev.includes(choiceId) 
          ? prev.filter(id => id !== choiceId)
          : [...prev, choiceId]
      );
      setIsDirty(true);
    } else {
      // For single select, save immediately (no confirmation needed)
      setIsSaving(true);
      try {
        const choice = question.answers?.find(a => a.id === choiceId);
        
        const answerRecord: QAAnswerRecord = {
          id: existingAnswer?.id,
          question: question.question,
          setting_id: settingId,
          question_id: question.id,
          parent_model: parent_model,
          parent_id: parentId,
          status: 'answered',
          answer_id: choiceId,
          answer: choice?.answer,
        };

        await onSave(answerRecord);
        setSelectedChoices([choiceId]);
        setIsDirty(false);
      } catch (err) {
        console.error('Failed to save answer:', err);
      } finally {
        setIsSaving(false);
      }
    }
  };

  const handleFreeformChange = (text: string) => {
    setFreeformText(text);
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
        parent_model: parent_model,
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

  // Determine if we need an expandable section (for freeform only - images now inline)
  const needsExpansion = options.allow_freeform;
  const imageInputRef = useRef<HTMLInputElement>(null);

  const handleInlineImageSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    if (files.length === 0) return;

    const remaining = options.image_max - images.length;
    const toAdd = files.slice(0, remaining).map(file => ({
      id: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
      file,
      preview: URL.createObjectURL(file),
      filename: file.name,
    }));

    setImages([...images, ...toAdd]);
    setIsDirty(true);
    if (imageInputRef.current) imageInputRef.current.value = '';
  };

  const handleInlineImageRemove = (index: number) => {
    const img = images[index];
    if (img.preview && img.file) {
      URL.revokeObjectURL(img.preview);
    }
    setImages(images.filter((_, i) => i !== index));
    setIsDirty(true);
  };

  const imageAccept = options.image_types.map(t => 
    t.startsWith('.') ? t : `.${t}`
  ).join(',');

  return (
    <div className="border rounded-lg border-slate-200 dark:border-slate-600 p-2">
      {/* Question row with inline choices and images */}
      <div className="flex items-center gap-1.5 flex-wrap">
        <FaQuestionCircle className="text-blue-500 flex-shrink-0" size={11} />
        <span className="text-xs font-medium text-slate-700 dark:text-slate-300">
          {question.question}
          {options.require_image && <span className="text-red-500 ml-0.5">*</span>}
        </span>
        
        {/* Inline choices for radio/checkbox */}
        {question.answers && question.answers.length > 0 && (
          <div className="flex flex-wrap gap-1 ml-1">
            {question.answers.map(choice => (
              <label 
                key={choice.id}
                className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded cursor-pointer transition-colors text-[11px] ${
                  selectedChoices.includes(choice.id)
                    ? 'bg-blue-100 dark:bg-blue-900/40 border border-blue-300 dark:border-blue-600 text-blue-700 dark:text-blue-300'
                    : 'bg-slate-50 dark:bg-slate-700/50 border border-slate-200 dark:border-slate-600 hover:border-blue-300'
                } ${!canEdit ? 'cursor-default' : ''}`}
                onClick={(e) => e.stopPropagation()}
              >
                <input
                  type={options.allow_multiple ? 'checkbox' : 'radio'}
                  name={`q_${question.id}`}
                  checked={selectedChoices.includes(choice.id)}
                  onChange={() => handleChoiceToggle(choice.id)}
                  disabled={!canEdit}
                  className="text-blue-600 w-2.5 h-2.5"
                />
                <span>{choice.answer}</span>
              </label>
            ))}
          </div>
        )}

        {/* Inline image thumbnails */}
        {images.length > 0 && (
          <div className="flex items-center gap-1 ml-1">
            {images.map((img, index) => (
              <div 
                key={img.id || index} 
                className="relative w-6 h-6 rounded border border-slate-200 dark:border-slate-600 overflow-hidden group"
              >
                <img 
                  src={img.preview || img.path} 
                  alt={img.filename}
                  className="w-full h-full object-cover"
                />
                {canEdit && (
                  <button
                    onClick={(e) => { e.stopPropagation(); handleInlineImageRemove(index); }}
                    className="absolute inset-0 bg-red-500/80 text-white flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                  >
                    <FaTimes size={8} />
                  </button>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Inline add image button */}
        {canEdit && images.length < options.image_max && (
          <>
            <button
              type="button"
              onClick={(e) => { e.stopPropagation(); imageInputRef.current?.click(); }}
              className="p-1 text-slate-400 hover:text-blue-500 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded"
              title="Add image"
            >
              <FaImage size={10} />
            </button>
            <input
              ref={imageInputRef}
              type="file"
              accept={imageAccept}
              multiple={options.image_max - images.length > 1}
              onChange={handleInlineImageSelect}
              className="hidden"
            />
          </>
        )}
        
        <span className={`px-1 py-0.5 rounded text-[10px] ml-auto ${statusColor}`}>
          {status === 'answered' ? <FaCheck size={7} className="inline" /> : <FaClock size={7} className="inline" />}
        </span>
        {needsExpansion && (
          <div 
            className="cursor-pointer p-0.5 hover:bg-slate-100 dark:hover:bg-slate-700 rounded"
            onClick={() => setIsExpanded(!isExpanded)}
          >
            {isExpanded ? <FaChevronUp size={10} /> : <FaChevronDown size={10} />}
          </div>
        )}
      </div>

      {/* Expanded section for freeform only */}
      {isExpanded && needsExpansion && (
        <div className="mt-1.5 ml-4 space-y-1.5">
          {/* Freeform input */}
          {options.allow_freeform && (
            <div>
              <textarea
                value={freeformText}
                onChange={(e) => handleFreeformChange(e.target.value)}
                placeholder={question.answers?.length ? 'Or enter custom answer...' : 'Enter your answer...'}
                className="w-full px-2 py-1 text-xs border rounded dark:bg-slate-700 dark:border-slate-600 focus:ring-1 focus:ring-blue-500"
                rows={2}
                disabled={!canEdit}
              />
            </div>
          )}

          {/* Save button - for multi-select or freeform */}
          {canEdit && isDirty && (options.allow_multiple || options.allow_freeform) && (
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
      <div className="bg-white dark:bg-slate-800 rounded-lg p-3 w-80 max-w-full mx-4">
        <h3 className="text-xs font-semibold mb-3 text-slate-700 dark:text-slate-200">
          {entry ? 'Edit Q&A' : 'Add Question'}
        </h3>
        
        <form onSubmit={handleSubmit} className="space-y-2">
          <div>
            <label className="block text-[10px] text-slate-600 dark:text-slate-400 mb-0.5">Question</label>
            <textarea
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              className="w-full px-2 py-1 text-xs border rounded dark:bg-slate-700 dark:border-slate-600"
              rows={2}
              required
              autoFocus
            />
          </div>

          <div>
            <label className="block text-[10px] text-slate-600 dark:text-slate-400 mb-0.5">Answer (optional)</label>
            <textarea
              value={answer}
              onChange={(e) => setAnswer(e.target.value)}
              className="w-full px-2 py-1 text-xs border rounded dark:bg-slate-700 dark:border-slate-600"
              rows={2}
            />
          </div>

          <div className="flex justify-end gap-2 mt-3">
            <button
              type="button"
              onClick={onClose}
              className="px-2 py-1 text-xs text-slate-600 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-700 rounded"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-2 py-1 text-xs bg-blue-500 text-white rounded hover:bg-blue-600"
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
  parent_model,
  parentId,
  onAnswersChange,
  onLinksChange,
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
  const hasApiPersistence = !!(parent_model && parentId);
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
          hasApiPersistence ? getQAAnswers(parent_model!, parentId!) : Promise.resolve([]),
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
  }, [questionGroup, parent_model, parentId, isTemplateMode, hasApiPersistence]);

  // Helper to build links array from all answers
  const buildLinksArray = useCallback((template: QAAnswerRecord[], freeform: QAAnswerRecord[]) => {
    const allAnswers = [...template, ...freeform];
    return allAnswers.filter(a => a.id).map(a => ({ id: a.id! }));
  }, []);

  // Template mode: handle save
  const handleSaveTemplateAnswer = useCallback(async (answer: QAAnswerRecord) => {
    const saved = await saveQAAnswer(answer);
    if (saved) {
      setTemplateAnswers(prev => {
        const existing = prev.findIndex(a => a.question_id === answer.question_id);
        let updated: QAAnswerRecord[];
        if (existing >= 0) {
          updated = [...prev];
          updated[existing] = saved;
        } else {
          updated = [...prev, saved];
        }
        // Update links with new state
        onLinksChange?.(buildLinksArray(updated, freeformAnswers));
        onAnswersChange?.([...updated, ...freeformAnswers]);
        return updated;
      });
    }
  }, [freeformAnswers, onAnswersChange, onLinksChange, buildLinksArray]);

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
      parent_model: parent_model!,
      parent_id: parentId!,
      status: entry.answer ? 'answered' : 'open',
      // No question_id means it's a freeform question
    };

    const saved = await saveQAAnswer(answerRecord);
    if (saved) {
      setFreeformAnswers(prev => {
        let updated: QAAnswerRecord[];
        if (editingEntry?.id) {
          updated = prev.map(a => a.id === editingEntry.id ? saved : a);
        } else {
          updated = [...prev, saved];
        }
        // Update links with new state
        onLinksChange?.(buildLinksArray(templateAnswers, updated));
        onAnswersChange?.([...templateAnswers, ...updated]);
        return updated;
      });
    }
  }, [hasApiPersistence, editingEntry, data, onChange, parent_model, parentId, templateAnswers, onAnswersChange, onLinksChange, buildLinksArray]);

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
        setFreeformAnswers(prev => {
          const updated = prev.filter((_, i) => i !== index);
          // Update links after deletion
          onLinksChange?.(buildLinksArray(templateAnswers, updated));
          return updated;
        });
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
        className="flex items-center justify-between px-3 py-2 bg-indigo-50 dark:bg-indigo-900/20 border-b border-indigo-200 dark:border-indigo-800 cursor-pointer rounded-t-lg"
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
        <div className={`${compact ? 'p-1.5' : 'p-3'} space-y-1.5`}>
          {/* Parent record not saved yet */}
          {isTemplateMode && !parentId ? (
            <div className="flex items-center gap-2 py-4 px-3 bg-amber-50 dark:bg-amber-900/20 rounded-lg border border-amber-200 dark:border-amber-700">
              <FaExclamationTriangle className="text-amber-500 flex-shrink-0" size={14} />
              <p className="text-xs text-amber-700 dark:text-amber-300">
                Save the record first to enable Q&A functionality.
              </p>
            </div>
          ) : isLoading ? (
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
                        parent_model={parent_model!}
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
                <div className="border-t border-slate-200 dark:border-slate-700 my-2 pt-1.5">
                  <span className="text-[10px] text-slate-400 font-medium">Additional Questions</span>
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
                <div className="text-center py-3 text-slate-400 text-xs">
                  <FaQuestionCircle size={18} className="mx-auto mb-1.5 opacity-50" />
                  <p>No questions yet</p>
                  {canEdit && allowFreeform && (
                    <button
                      onClick={handleAdd}
                      className="mt-1.5 text-indigo-600 hover:underline text-[10px]"
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
                  className="w-full mt-1.5 py-1.5 text-[10px] text-indigo-600 hover:bg-indigo-50 dark:hover:bg-indigo-900/20 rounded border border-dashed border-indigo-300 dark:border-indigo-700"
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

export default withDevIdentifier(QAPanel, 'QAPanel', 'teal');