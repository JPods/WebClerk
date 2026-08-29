/**
 * FileUploadPanel — reusable photo/video/file upload for any record.
 *
 * Every upload creates a Document record (model_name, record_id, role, path).
 * Phone camera opens directly via capture="environment".
 * Shows existing attachments from Document records linked to this record.
 *
 * Usage:
 *   <FileUploadPanel modelName="action" recordId="42" recordIda="ACT-001" />
 *   <FileUploadPanel modelName="item" recordId="100" recordIda="WIDGET-100" />
 *   <FileUploadPanel modelName="qa" recordId="55" recordIda="QA-055" />
 *
 * Rule: every upload → Document record. No exceptions.
 */
import { useState, useRef, useCallback, useEffect } from "react";
import { getRecord, getRecords, saveRecord } from "@/api/wcapi";
import { uploadDocument } from "@/apps/common/components/panels/documentUpload";
import { useDispatch } from "react-redux";
import { showToast } from "@/store/slices/toastSlice";

interface Props {
  modelName: string;
  recordId: string | number;
  recordIda?: string;
  /** Compact mode — just the upload button, no attachment list */
  compact?: boolean;
  className?: string;
}

interface Attachment {
  id: number;
  name: string;
  config?: {
    role?: string;
    path?: string;
    library_url?: string;
    archive_url?: string;
    mime_type?: string;
    size_bytes?: number;
    uploaded_dt?: string;
    inline_content_b64?: string;
  };
}

const PURPOSE_OPTIONS = [
  { value: "photo", label: "photo" },
  { value: "video", label: "video" },
  { value: "attachment", label: "attachment" },
  { value: "spec", label: "spec" },
  { value: "drawing", label: "drawing" },
  { value: "receipt", label: "receipt" },
  { value: "qa", label: "qa" },
  { value: "other", label: "other" },
];

interface PendingFile {
  file: File;
  purpose: string;
  description: string;
}

const FileUploadPanel: React.FC<Props> = ({
  modelName,
  recordId,
  recordIda,
  compact = false,
  className = "",
}) => {
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [uploading, setUploading] = useState(false);
  const [loadingDocs, setLoadingDocs] = useState(false);
  const [pendingFiles, setPendingFiles] = useState<PendingFile[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const dispatch = useDispatch();

  // Load existing Document records for this record
  const loadAttachments = useCallback(async () => {
    if (!recordId) return;
    setLoadingDocs(true);
    try {
      const res = await getRecords("document", {
        "config__parent_model": modelName,
        "config__parent_id": String(recordId),
        ordering: "-dt_created",
        limit: 50,
      }) as any;
      setAttachments(res?.results || []);
    } catch {
      // Silent — attachments are supplementary
    }
    setLoadingDocs(false);
  }, [modelName, recordId]);

  useEffect(() => {
    loadAttachments();
  }, [loadAttachments]);

  // When files are selected, open the metadata dialog
  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files?.length) return;

    const pending: PendingFile[] = [];
    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      const isVideo = file.type.startsWith("video/");
      const isImage = file.type.startsWith("image/");
      const defaultPurpose = isVideo ? "video" : isImage ? "photo" : "attachment";
      pending.push({ file, purpose: defaultPurpose, description: "" });
    }
    setPendingFiles(pending);
  }, []);

  const updatePending = (idx: number, field: 'purpose' | 'description', value: string) => {
    setPendingFiles(prev => prev.map((p, i) => i === idx ? { ...p, [field]: value } : p));
  };

  const cancelPending = () => {
    setPendingFiles([]);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const confirmUpload = useCallback(async () => {
    if (!pendingFiles.length) return;
    setUploading(true);

    // Capture browser geolocation for photos/videos taken on-site
    let geo: { lat: number; lng: number; accuracy?: number } | undefined;
    try {
      const pos = await new Promise<GeolocationPosition>((resolve, reject) =>
        navigator.geolocation.getCurrentPosition(resolve, reject, { timeout: 5000 })
      );
      geo = { lat: pos.coords.latitude, lng: pos.coords.longitude, accuracy: pos.coords.accuracy };
    } catch { /* geolocation unavailable or denied — proceed without */ }

    for (const pending of pendingFiles) {
      try {
        const result = await uploadDocument({
          file: pending.file,
          parent_model: modelName,
          parentId: Number(recordId),
          purpose: pending.purpose,
          description: pending.description || `${pending.purpose} for ${modelName} ${recordIda || recordId}`,
          geolocation: geo,
        });

        // Append to parent record's refs.links.document with denormalized data
        try {
          const parentRes = await getRecord(modelName, Number(recordId));
          const parent = parentRes?.record || parentRes;
          const existing = parent?.refs?.links?.document || [];
          const ids = existing.map((l: any) => typeof l === 'number' ? l : l?.id).filter(Boolean);
          if (!ids.includes(result.document.id)) {
            const newLink = {
              id: result.document.id,
              purpose: pending.purpose,
              description: pending.description,
              size_bytes: result.document.size_bytes,
              name: result.document.name,
              mime_type: result.document.mime_type,
              ...(geo ? { lat: geo.lat, lng: geo.lng } : {}),
            };
            const newLinks = [...existing, newLink];
            await saveRecord(modelName, {
              id: Number(recordId),
              'refs.links.document': newLinks,
            });
            window.dispatchEvent(new CustomEvent('refs-links-changed', {
              detail: { model: modelName, id: Number(recordId) },
            }));
          }
        } catch { /* refs.links update failed — document still exists */ }

        dispatch(showToast({
          message: `${pending.file.name} uploaded (${(pending.file.size / 1024).toFixed(0)}KB)`,
          type: "success",
        }));
      } catch {
        dispatch(showToast({ message: `Failed to upload ${pending.file.name}`, type: "error" }));
      }
    }

    setPendingFiles([]);
    setUploading(false);
    if (fileInputRef.current) fileInputRef.current.value = "";
    if (!compact) loadAttachments();
  }, [pendingFiles, modelName, recordId, recordIda, dispatch, compact, loadAttachments]);

  const roleIcon = (role?: string) => {
    switch (role) {
      case "photo": return "📷";
      case "video": return "🎥";
      case "spec": return "📋";
      case "tn": return "🖼";
      default: return "📎";
    }
  };

  return (
    <div className={`${className}`}>
      {/* Upload button */}
      <div className="flex items-center gap-2">
        <label className="cursor-pointer inline-flex items-center gap-1 text-xs font-medium text-indigo-600 dark:text-indigo-400 hover:underline">
          + Photo / Video / File
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*,video/*,.pdf,.doc,.docx"
            multiple
            capture="environment"
            onChange={handleFileSelect}
            className="hidden"
          />
        </label>
        {uploading && <span className="text-[10px] text-gray-400">Uploading...</span>}
        {compact && attachments.length > 0 && (
          <span className="text-[10px] text-gray-400">{attachments.length} file{attachments.length !== 1 ? 's' : ''}</span>
        )}
      </div>

      {/* Upload metadata dialog */}
      {pendingFiles.length > 0 && !uploading && (
        <div className="mt-2 p-2 rounded border border-indigo-500/30 bg-gray-900/50">
          {pendingFiles.map((p, idx) => (
            <div key={idx} className="flex items-center gap-2 mb-2 last:mb-0">
              <span className="text-[11px] text-gray-300 truncate" style={{ minWidth: 80, maxWidth: 140 }}>
                {p.file.name}
              </span>
              <select
                value={p.purpose}
                onChange={e => updatePending(idx, 'purpose', e.target.value)}
                className="text-[11px] bg-gray-800 text-gray-200 border border-gray-600 rounded px-1 py-0.5"
                style={{ fontSize: 16 }}
              >
                {PURPOSE_OPTIONS.map(o => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
              <input
                type="text"
                value={p.description}
                onChange={e => updatePending(idx, 'description', e.target.value)}
                placeholder="description"
                className="text-[11px] bg-gray-800 text-gray-200 border border-gray-600 rounded px-1 py-0.5 flex-1"
                style={{ fontSize: 16, minWidth: 100 }}
              />
              <span className="text-[9px] text-gray-500">
                {p.file.size > 1048576
                  ? `${(p.file.size / 1048576).toFixed(1)}MB`
                  : `${(p.file.size / 1024).toFixed(0)}KB`}
              </span>
            </div>
          ))}
          <div className="flex gap-2 mt-2">
            <button
              onClick={confirmUpload}
              className="text-[11px] px-3 py-1 rounded bg-indigo-600 text-white hover:bg-indigo-500"
            >
              Upload {pendingFiles.length > 1 ? `(${pendingFiles.length})` : ''}
            </button>
            <button
              onClick={cancelPending}
              className="text-[11px] px-3 py-1 rounded text-gray-400 hover:text-gray-200"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Attachment list (non-compact mode) */}
      {!compact && attachments.length > 0 && (
        <div className="mt-2 space-y-1">
          {attachments.map((doc) => {
            const isImage = doc.config?.mime_type?.startsWith("image/");
            return (
              <div
                key={doc.id}
                className="flex items-center gap-2 text-[11px] text-gray-600 dark:text-gray-400 py-0.5 px-1 rounded hover:bg-gray-50 dark:hover:bg-gray-800"
              >
                <span>{roleIcon(doc.config?.role)}</span>
                {isImage && (
                  <img
                    src={`/wcapi/document/${doc.id}/`}
                    alt={doc.name}
                    className="h-6 w-6 rounded object-cover"
                    loading="lazy"
                  />
                )}
                <span className="truncate flex-1">{doc.name}</span>
                {doc.config?.size_bytes && (
                  <span className="text-[9px] text-gray-400">
                    {doc.config.size_bytes > 1048576
                      ? `${(doc.config.size_bytes / 1048576).toFixed(1)}MB`
                      : `${(doc.config.size_bytes / 1024).toFixed(0)}KB`}
                  </span>
                )}
                <a
                  href={`/wcapi/document/${doc.id}/`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-[9px] text-indigo-500 hover:underline"
                >
                  open
                </a>
              </div>
            );
          })}
        </div>
      )}

      {!compact && !loadingDocs && attachments.length === 0 && pendingFiles.length === 0 && (
        <p className="text-[10px] text-gray-400 mt-1">No files attached. Use phone camera or choose a file.</p>
      )}
    </div>
  );
};

export default FileUploadPanel;
export { FileUploadPanel };
