/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
/**
 * EmailGatePanel — Pre-entry gate for new contacts.
 *
 * Displayed at the top of ContactDetail3 in "add" mode.
 * Forces the operator to enter an email (or type "later" to skip) before
 * revealing the full form.  If an existing contact matches, the operator
 * can open it instead of creating a duplicate.
 *
 * Two personas:
 *  1. **Staff / Admin / Rep** — types an email, gets instant search results.
 *     Can bypass by typing "later".
 *  2. **End-user (self-registration)** — enters their email for a
 *     confirmation flow. The parent page supplies the confirmed contact
 *     record (already has an ID), so this gate never renders.
 *
 * ┌─ Enter email to begin ────────────────────────────────┐
 * │  email :  [_____________________]                     │
 * │                                                       │
 * │  ┌ Existing matches ───────────────────────────────┐  │
 * │  │ #42  user@example.com   John Doe   Acme  ► Open │  │
 * │  │ #87  user@alt.com       Jane Doe   Beta  ► Open │  │
 * │  └────────────────────────────────────────────────┘  │
 * │                                                       │
 * │  [ Continue with new contact ]     Type "later" to skip│
 * └───────────────────────────────────────────────────────┘
 */

import React, { useState, useEffect, useCallback, useRef } from "react";
import {
  FaSearch,
  FaSpinner,
  FaArrowRight,
  FaExternalLinkAlt,
} from "react-icons/fa";
import { Mail } from "lucide-react";
import { getRecords } from "@/api/wcapi";
import { withDevIdentifier } from '@/components/common/DevIdentifier';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface EmailGateResult {
  /** "proceed" = continue to add form; "open" = switch to existing record */
  action: "proceed" | "open";
  /** The entered email (may be empty if user typed "later") */
  email: string;
  /** If action === "open", the existing contact record to edit */
  existingContact?: any;
  /** Whether the gate was bypassed with "later" */
  skipped: boolean;
}

export interface EmailGatePanelProps {
  /** Called when the user passes through the gate */
  onComplete: (result: EmailGateResult) => void;
  /** Called if the user cancels add mode entirely */
  onCancel?: () => void;
  /** Is this user a staff/admin/rep? (affects messaging) */
  isStaff?: boolean;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const EmailGatePanel: React.FC<EmailGatePanelProps> = ({
  onComplete,
  onCancel,
  isStaff = true,
}) => {
  const [email, setEmail] = useState("");
  const [searching, setSearching] = useState(false);
  const [matches, setMatches] = useState<any[]>([]);
  const [hasSearched, setHasSearched] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Focus the input on mount
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  // Debounced search as user types
  useEffect(() => {
    const trimmed = email.trim().toLowerCase();

    // "later" bypass — don't search
    if (trimmed === "later") {
      setMatches([]);
      setHasSearched(false);
      return;
    }

    // Need at least 3 chars to search
    if (trimmed.length < 3) {
      setMatches([]);
      setHasSearched(false);
      return;
    }

    if (debounceRef.current) clearTimeout(debounceRef.current);

    debounceRef.current = setTimeout(async () => {
      setSearching(true);
      try {
        const res: any = await getRecords("contact", {
          search: trimmed,
          q: trimmed,
          limit: 10,
        });
        const results = (res?.results || []).filter((r: any) => r?.id);
        setMatches(results);
        setHasSearched(true);
      } catch {
        setMatches([]);
        setHasSearched(true);
      } finally {
        setSearching(false);
      }
    }, 400);

    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [email]);

  /** User wants to open an existing contact */
  const handleOpenExisting = useCallback(
    (contact: any) => {
      onComplete({
        action: "open",
        email: email.trim(),
        existingContact: contact,
        skipped: false,
      });
    },
    [email, onComplete],
  );

  /** User wants to proceed with creating a new contact */
  const handleProceed = useCallback(() => {
    const trimmed = email.trim().toLowerCase();
    const skipped = trimmed === "later" || trimmed === "";
    onComplete({
      action: "proceed",
      email: skipped ? "" : trimmed,
      skipped,
    });
  }, [email, onComplete]);

  /** Handle Enter key */
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter") {
        e.preventDefault();
        const trimmed = email.trim().toLowerCase();
        if (trimmed === "later") {
          handleProceed();
        } else if (trimmed.length >= 3 && matches.length === 0 && hasSearched) {
          handleProceed();
        }
      }
    },
    [email, matches, hasSearched, handleProceed],
  );

  const isLater = email.trim().toLowerCase() === "later";
  const isValidEmail = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim());
  const canProceed =
    isLater || (email.trim().length >= 3 && hasSearched && !searching);

  return (
    <div className="max-w-xl mx-auto py-8 px-4">
      {/* Title */}
      <div className="text-center mb-6">
        <div className="inline-flex items-center justify-center w-12 h-12 rounded-full mb-3" style={{ background: 'var(--db-row-active)' }}>
          <Mail size={24} style={{ color: 'var(--db-accent)' }} />
        </div>
        <h2 className="text-lg font-semibold" style={{ color: 'var(--db-text)' }}>
          {isStaff ? "New Contact — Enter Email First" : "Enter Your Email"}
        </h2>
        <p className="text-sm mt-1" style={{ color: 'var(--db-text-muted)' }}>
          {isStaff
            ? 'Search for an existing contact before creating a new one. Type "later" to skip.'
            : "We'll check if you already have an account."}
        </p>
      </div>

      {/* Email input */}
      <div className="relative mb-4">
        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
          {searching ? (
            <FaSpinner className="animate-spin" style={{ color: 'var(--db-text-dim)' }} size={14} />
          ) : (
            <FaSearch style={{ color: 'var(--db-text-dim)' }} size={14} />
          )}
        </div>
        <input
          ref={inputRef}
          type="text"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder='Email address (or type "later" to skip)'
          className="w-full pl-10 pr-4 py-3 text-sm rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-shadow"
          style={{ background: 'var(--db-input-bg)', border: '1px solid var(--db-input-border)', color: 'var(--db-text)' }}
          autoComplete="email"
        />
      </div>

      {/* "later" indicator */}
      {isLater && (
        <div className="mb-4 px-4 py-3 border rounded-xl" style={{ background: 'var(--db-surface-alt)', borderColor: 'var(--db-border)' }}>
          <p className="text-sm" style={{ color: 'var(--db-text-muted)' }}>
            <strong>Skip mode:</strong> The form will open without an email
            pre-filled. You can add the email later.
          </p>
        </div>
      )}

      {/* Search results */}
      {hasSearched && !isLater && matches.length > 0 && (
        <div className="mb-4">
          <h3 className="text-xs font-semibold uppercase tracking-wider mb-2" style={{ color: 'var(--db-text-muted)' }}>
            Existing contacts found ({matches.length})
          </h3>
          <div className="rounded-xl overflow-hidden divide-y" style={{ border: '1px solid var(--db-border)', divideColor: 'var(--db-border-light)' }}>
            {matches.map((contact: any) => (
              <button
                key={contact.id}
                type="button"
                onClick={() => handleOpenExisting(contact)}
                className="w-full flex items-center gap-3 px-4 py-3 text-left transition-colors group db-list-row"
              >
                <span className="text-xs font-mono shrink-0" style={{ color: 'var(--db-text-dim)' }}>
                  #{contact.id}
                </span>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium truncate" style={{ color: 'var(--db-text)' }}>
                    {contact.attention ||
                      [contact.name_first, contact.name_last]
                        .filter(Boolean)
                        .join(" ") ||
                      contact.email ||
                      `Contact #${contact.id}`}
                  </div>
                  <div className="text-xs truncate" style={{ color: 'var(--db-text-muted)' }}>
                    {contact.email}
                    {contact.company ? ` · ${contact.company}` : ""}
                    {contact.role ? ` · ${contact.role}` : ""}
                  </div>
                </div>
                <span className="shrink-0 flex items-center gap-1 text-xs font-medium opacity-0 group-hover:opacity-100 transition-opacity" style={{ color: 'var(--db-accent)' }}>
                  Open <FaExternalLinkAlt size={10} />
                </span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* No matches message */}
      {hasSearched && !isLater && matches.length === 0 && !searching && (
        <div className="mb-4 px-4 py-3 border rounded-xl" style={{ background: 'var(--db-surface-alt)', borderColor: 'var(--db-border)' }}>
          <p className="text-sm" style={{ color: 'var(--db-text)' }}>
            No existing contacts match{" "}
            <strong className="font-mono">{email.trim()}</strong>. You can
            create a new contact.
          </p>
        </div>
      )}

      {/* Action buttons */}
      <div className="flex items-center justify-between gap-3">
        {onCancel && (
          <button
            type="button"
            onClick={onCancel}
            className="px-4 py-2.5 text-sm font-medium rounded-xl transition-colors"
            style={{ color: 'var(--db-text)', background: 'var(--db-surface-alt)' }}
          >
            Cancel
          </button>
        )}

        <button
          type="button"
          onClick={handleProceed}
          disabled={!canProceed}
          className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 text-sm font-medium disabled:opacity-50 rounded-xl transition-colors"
          style={{ background: 'var(--db-btn-primary)', color: '#fff' }}
        >
          {isLater ? (
            <>Skip — Continue without email</>
          ) : (
            <>
              Continue with new contact
              <FaArrowRight size={12} />
            </>
          )}
        </button>
      </div>
    </div>
  );
};

export default withDevIdentifier(EmailGatePanel, 'EmailGatePanel', 'teal', 'apps/common/components/panels/EmailGatePanel.tsx');