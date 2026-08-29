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
import { getRecords } from "@/api/wcapi";
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

  const handleUpload = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files?.length) return;
    setUploading(true);

    // Capture browser geolocation for photos/videos taken on-site
    let geo: { lat: number; lng: number; accuracy?: number } | undefined;
    try {
      const pos = await new Promise<GeolocationPosition>((resolve, reject) =>
        navigator.geolocation.getCurrentPosition(resolve, reject, { timeout: 5000 })
      );
      geo = { lat: pos.coords.latitude, lng: pos.coords.longitude, accuracy: pos.coords.accuracy };
    } catch { /* geolocation unavailable or denied — proceed without */ }

    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      const isVideo = file.type.startsWith("video/");
      const isImage = file.type.startsWith("image/");
      const purpose = isVideo ? "video" : isImage ? "photo" : "attachment";

      try {
        await uploadDocument({
          file,
          parent_model: modelName,
          parentId: Number(recordId),
          purpose,
          description: `${purpose} for ${modelName} ${recordIda || recordId}`,
          geolocation: geo,
        });

        dispatch(showToast({
          message: `${file.name} uploaded (${(file.size / 1024).toFixed(0)}KB)`,
          type: "success",
        }));
      } catch {
        dispatch(showToast({ message: `Failed to upload ${file.name}`, type: "error" }));
      }
    }

    setUploading(false);
    if (fileInputRef.current) fileInputRef.current.value = "";
    if (!compact) loadAttachments();
  }, [modelName, recordId, recordIda, dispatch, compact, loadAttachments]);

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
            onChange={handleUpload}
            className="hidden"
          />
        </label>
        {uploading && <span className="text-[10px] text-gray-400">Uploading...</span>}
        {compact && attachments.length > 0 && (
          <span className="text-[10px] text-gray-400">{attachments.length} file{attachments.length !== 1 ? 's' : ''}</span>
        )}
      </div>

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

      {!compact && !loadingDocs && attachments.length === 0 && (
        <p className="text-[10px] text-gray-400 mt-1">No files attached. Use phone camera or choose a file.</p>
      )}
    </div>
  );
};

export default FileUploadPanel;
export { FileUploadPanel };
