/**
 * FileUploadPanel — photo/video/file upload for any record.
 *
 * Every upload creates a Document record and lists it in the record's refs.links.document;
 * the save door lists the record back on the document (two-sided links, Bill 2026-10-31).
 * Phone camera opens directly via capture="environment". The record's documents are the
 * Documents panel (the shared list); this is only the way in.
 *
 * Usage:
 *   <FileUploadPanel modelName="action" recordId="42" recordIda="ACT-001" />
 *   <FileUploadPanel modelName="item" recordId="100" recordIda="WIDGET-100" />
 *   <FileUploadPanel modelName="qa" recordId="55" recordIda="QA-055" />
 *
 * Rule: every upload → Document record. No exceptions.
 */
import { useState, useRef, useCallback } from "react";
import { getRecord, saveRecord } from "@/api/wcapi";
import { uploadDocument } from "@/apps/common/components/panels/documentUpload";
import { useDispatch } from "react-redux";
import { showToast } from "@/store/slices/toastSlice";

interface Props {
  modelName: string;
  recordId: string | number;
  recordIda?: string;
  className?: string;
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
  className = "",
}) => {
  const [uploading, setUploading] = useState(false);
  const [pendingFiles, setPendingFiles] = useState<PendingFile[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const dispatch = useDispatch();

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

        // The record lists the document; its other side is written by the save door.
        try {
          const parentRes = await getRecord(modelName, Number(recordId));
          const parent = parentRes?.record || parentRes;
          const existing = parent?.refs?.links?.document || [];
          const ids = existing.map((l: any) => typeof l === 'number' ? l : l?.id).filter(Boolean);
          if (!ids.includes(result.document.id)) {
            // The link is the id: the panel reads the document itself, never a copy.
            const newLinks = [...existing, { id: result.document.id }];
            await saveRecord(modelName, {
              id: Number(recordId),
              'refs.links.document': newLinks,
            });
          }
        } catch (err: any) {
          dispatch(showToast({ message: `${pending.file.name} uploaded but not linked to this ${modelName}: ${err?.message || err}`, type: "error" }));
        }

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
  }, [pendingFiles, modelName, recordId, recordIda, dispatch]);

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

    </div>
  );
};

export default FileUploadPanel;
export { FileUploadPanel };
