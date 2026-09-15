/**
 * VCardImportDialog — paste or drop a .vcf file to import a contact.
 *
 * Parses vCard from Google Contacts, Apple Contacts, Dot, or any app.
 * Shows preview with company match detection before creating records.
 *
 * LastChecked: 2026-08-24 | WhereUsed: FlightSimConsole, standalone | WhoCreated: Claude
 */
import React, { useState, useCallback, useRef } from "react";
import { manageAction } from "../../api/wcapi";
import "./VCardImportDialog.css";

interface VCardImportDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onImported?: (contactId: number, orgId?: number) => void;
  /** Pre-link to existing company */
  customerId?: number;
}

interface PreviewData {
  contact_fields: Record<string, string>;
  phone?: { number: string; type: string } | null;
  address?: Record<string, string> | null;
  org_name: string;
  existing_orgs: Array<{ id: number; display_name: string; status: string; org_type: string }>;
  existing_contacts: Array<{ id: number; ida: string; name_first: string; name_last: string; email: string }>;
  source_name: string;
  error?: string;
}

type Stage = "input" | "previewing" | "preview" | "importing" | "done";

const VCardImportDialog: React.FC<VCardImportDialogProps> = ({ isOpen, onClose, onImported, customerId }) => {
  const [vcardText, setVcardText] = useState("");
  const [stage, setStage] = useState<Stage>("input");
  const [preview, setPreview] = useState<PreviewData | null>(null);
  const [orgChoice, setOrgChoice] = useState<"existing" | "create">("create");
  const [selectedOrgId, setSelectedOrgId] = useState<number | null>(null);
  const [result, setResult] = useState<{ contact_id: number; org_id?: number; message: string } | null>(null);
  const [error, setError] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const reset = useCallback(() => {
    setVcardText("");
    setStage("input");
    setPreview(null);
    setOrgChoice("create");
    setSelectedOrgId(null);
    setResult(null);
    setError("");
  }, []);

  const handleClose = () => {
    reset();
    onClose();
  };

  const handlePreview = async () => {
    if (!vcardText.trim()) return;
    setStage("previewing");
    setError("");
    try {
      const res = await manageAction("preview_vcard", { vcard_text: vcardText });
      const data = res?.data?.data ?? res?.data ?? res;
      if (data?.error) {
        setError(data.error);
        setStage("input");
        return;
      }
      setPreview(data as PreviewData);
      // Auto-select first existing org if found
      if (data.existing_orgs?.length > 0) {
        setOrgChoice("existing");
        setSelectedOrgId(data.existing_orgs[0].id);
      }
      setStage("preview");
    } catch (e: any) {
      setError(e?.message || "Preview failed");
      setStage("input");
    }
  };

  const handleImport = async () => {
    if (!preview) return;
    setStage("importing");
    setError("");
    try {
      const params: Record<string, any> = {
        contact_fields: preview.contact_fields,
        phone: preview.phone,
        address: preview.address,
        source_name: preview.source_name,
      };
      // Link to existing company if provided via prop
      if (customerId) {
        params.org_id = customerId;
      } else if (preview.org_name) {
        if (orgChoice === "existing" && selectedOrgId) {
          params.org_id = selectedOrgId;
        } else {
          params.create_org = { display_name: preview.org_name, org_type: "customer" };
        }
      }
      const res = await manageAction("import_vcard", params);
      const data = res?.data?.data ?? res?.data ?? res;
      if (data?.error) {
        setError(data.error);
        setStage("preview");
        return;
      }
      setResult(data);
      setStage("done");
      onImported?.(data.contact_id, data.org_id);
    } catch (e: any) {
      setError(e?.message || "Import failed");
      setStage("preview");
    }
  };

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    const file = e.dataTransfer?.files[0];
    if (file?.name.endsWith(".vcf")) {
      const reader = new FileReader();
      reader.onload = () => setVcardText(reader.result as string);
      reader.readAsText(file);
    }
  }, []);

  const handlePaste = useCallback((e: React.ClipboardEvent) => {
    const text = e.clipboardData?.getData("text") || "";
    if (text.includes("BEGIN:VCARD")) {
      e.preventDefault();
      setVcardText(text);
    }
  }, []);

  if (!isOpen) return null;

  const cf = preview?.contact_fields;

  return (
    <div className="vcard-overlay" onClick={handleClose}>
      <div className="vcard-dialog" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="vcard-header">
          <span className="vcard-title">Import Contact</span>
          <button className="vcard-close" onClick={handleClose}>&times;</button>
        </div>

        {/* Body */}
        <div className="vcard-body">
          {/* Stage: Input */}
          {(stage === "input" || stage === "previewing") && (
            <>
              <textarea
                ref={textareaRef}
                className="vcard-textarea"
                value={vcardText}
                onChange={(e) => setVcardText(e.target.value)}
                onDrop={handleDrop}
                onDragOver={(e) => e.preventDefault()}
                onPaste={handlePaste}
                placeholder={"Paste vCard here, or drag-drop a .vcf file\n\nBEGIN:VCARD\nVERSION:3.0\nFN:John Doe\n..."}
                disabled={stage === "previewing"}
              />
              <div className="vcard-dropzone-hint">
                Google Contacts, Apple Contacts, Dot, or any .vcf file
              </div>
            </>
          )}

          {/* Stage: Preview */}
          {stage === "preview" && cf && (
            <>
              <div className="vcard-preview-section">
                <div className="vcard-preview-label">Contact</div>
                <div className="vcard-preview-grid">
                  {cf.name_first && <><span className="vcard-preview-field">first</span><span className="vcard-preview-value">{cf.name_first}</span></>}
                  {cf.name_last && <><span className="vcard-preview-field">last</span><span className="vcard-preview-value">{cf.name_last}</span></>}
                  {cf.email && <><span className="vcard-preview-field">email</span><span className="vcard-preview-value">{cf.email}</span></>}
                  {cf.title && <><span className="vcard-preview-field">title</span><span className="vcard-preview-value">{cf.title}</span></>}
                  {cf.company && <><span className="vcard-preview-field">company</span><span className="vcard-preview-value">{cf.company}</span></>}
                  {preview.phone?.number && <><span className="vcard-preview-field">phone</span><span className="vcard-preview-value">{preview.phone.number}</span></>}
                  {preview.address?.city && <><span className="vcard-preview-field">address</span><span className="vcard-preview-value">{[preview.address.address1, preview.address.city, preview.address.state, preview.address.zip].filter(Boolean).join(", ")}</span></>}
                  <span className="vcard-preview-field">source</span><span className="vcard-preview-value">{preview.source_name}</span>
                </div>
              </div>

              {/* Existing contact warning */}
              {preview.existing_contacts.length > 0 && (
                <div className="vcard-warning">
                  Contact with email {cf.email} already exists: {preview.existing_contacts[0].name_first} {preview.existing_contacts[0].name_last} ({preview.existing_contacts[0].ida})
                </div>
              )}

              {/* Company match */}
              {preview.org_name && (
                <div className="vcard-match-section">
                  <div className="vcard-match-title">
                    Company: {preview.org_name}
                  </div>
                  {preview.existing_orgs.length > 0 ? (
                    <>
                      {preview.existing_orgs.map((org) => (
                        <label key={org.id} className="vcard-match-option">
                          <input
                            type="radio"
                            name="org-choice"
                            checked={orgChoice === "existing" && selectedOrgId === org.id}
                            onChange={() => { setOrgChoice("existing"); setSelectedOrgId(org.id); }}
                          />
                          Add to existing: {org.display_name} ({org.status})
                        </label>
                      ))}
                      <label className="vcard-match-option">
                        <input
                          type="radio"
                          name="org-choice"
                          checked={orgChoice === "create"}
                          onChange={() => setOrgChoice("create")}
                        />
                        Create new customer: {preview.org_name}
                      </label>
                    </>
                  ) : (
                    <div style={{ fontSize: "12px", color: "var(--db-text-muted)" }}>
                      No existing match — will create new customer
                    </div>
                  )}
                </div>
              )}
            </>
          )}

          {/* Stage: Done */}
          {stage === "done" && result && (
            <div className="vcard-success">
              <div className="vcard-success-icon">&#10003;</div>
              <div className="vcard-success-message">{result.message}</div>
            </div>
          )}

          {/* Error */}
          {error && <div className="vcard-warning">{error}</div>}
        </div>

        {/* Footer */}
        <div className="vcard-footer">
          {stage === "input" && (
            <>
              <button className="vcard-btn" onClick={handleClose}>Cancel</button>
              <button className="vcard-btn vcard-btn-primary" onClick={handlePreview} disabled={!vcardText.trim()}>
                Preview
              </button>
            </>
          )}
          {stage === "previewing" && (
            <button className="vcard-btn" disabled>Parsing...</button>
          )}
          {stage === "preview" && (
            <>
              <button className="vcard-btn" onClick={() => { setStage("input"); setPreview(null); }}>Back</button>
              <button
                className="vcard-btn vcard-btn-primary"
                onClick={handleImport}
                disabled={preview?.existing_contacts && preview.existing_contacts.length > 0}
              >
                Import
              </button>
            </>
          )}
          {stage === "importing" && (
            <button className="vcard-btn" disabled>Importing...</button>
          )}
          {stage === "done" && (
            <button className="vcard-btn vcard-btn-primary" onClick={handleClose}>Done</button>
          )}
        </div>
      </div>
    </div>
  );
};

export default VCardImportDialog;
