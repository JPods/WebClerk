/**
 * ContactCard — Compact floating contact card.
 * Shows photo, name, phone, email. Shift-click from any assigned_to label.
 */
import { useEffect, useState } from "react";
import { getRecord } from "@/api/wcapi";
import { withDevIdentifier } from '@/components/common/DevIdentifier';

interface ContactCardProps {
  contactId: string | number;
  position: { x: number; y: number };
  onClose: () => void;
}

function ContactCard({ contactId, position, onClose }: ContactCardProps) {
  const [data, setData] = useState<any>(null);

  useEffect(() => {
    if (!contactId) return;
    getRecord("contact", Number(contactId)).then((resp: any) => {
      const r = resp?.record || resp;
      if (r) setData(r);
    }).catch(() => {});
  }, [contactId]);

  if (!data) {
    return (
      <div
        className="fixed z-50 rounded-lg border border-gray-200 bg-white px-4 py-3 shadow-xl dark:border-gray-700 dark:bg-gray-900"
        style={{ left: position.x, top: position.y }}
      >
        <span className="text-xs text-gray-400">Loading...</span>
      </div>
    );
  }

  const name = [data.name_first, data.name_last].filter(Boolean).join(" ") || data.email || "—";
  const phone = data.phone || data.phone_id || "";
  const email = data.email || "";
  const company = data.company || "";
  const title = data.title || "";
  const initials = name.split(/\s+/).map((w: string) => w[0]).join("").toUpperCase().slice(0, 2);
  const photoUrl = data.metadata?.images?.photo?.sm || data.metadata?.images?.photo?.tn || null;

  return (
    <>
      <div className="fixed inset-0 z-40" onClick={onClose} />
      <div
        className="fixed z-50 w-64 rounded-lg border border-gray-200 bg-white shadow-xl dark:border-gray-700 dark:bg-gray-900"
        style={{ left: position.x, top: position.y }}
      >
        <div className="flex items-center gap-3 px-3 py-2.5">
          {/* Avatar */}
          {photoUrl ? (
            <img src={photoUrl} alt={name} className="h-10 w-10 shrink-0 rounded-full object-cover" />
          ) : (
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-indigo-100 text-sm font-bold text-indigo-700 dark:bg-indigo-900 dark:text-indigo-300">
              {initials}
            </div>
          )}
          <div className="min-w-0 flex-1">
            <div className="truncate text-sm font-medium text-gray-900 dark:text-white">{name}</div>
            {title && <div className="truncate text-[11px] text-gray-500 dark:text-gray-400">{title}</div>}
            {company && <div className="truncate text-[11px] text-gray-500 dark:text-gray-400">{company}</div>}
          </div>
          <button onClick={onClose} className="shrink-0 rounded p-0.5 text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800">
            <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M18 6L6 18M6 6l12 12" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </button>
        </div>

        {(phone || email) && (
          <div className="border-t border-gray-100 px-3 py-2 dark:border-gray-800">
            {phone && (
              <a href={`tel:${phone}`} className="flex items-center gap-2 py-0.5 text-xs text-blue-600 hover:underline dark:text-blue-400">
                <svg className="h-3 w-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M22 16.92v3a2 2 0 01-2.18 2 19.79 19.79 0 01-8.63-3.07 19.5 19.5 0 01-6-6 19.79 19.79 0 01-3.07-8.67A2 2 0 014.11 2h3a2 2 0 012 1.72c.127.96.361 1.903.7 2.81a2 2 0 01-.45 2.11L8.09 9.91a16 16 0 006 6l1.27-1.27a2 2 0 012.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0122 16.92z" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
                {phone}
              </a>
            )}
            {email && (
              <a href={`mailto:${email}`} className="flex items-center gap-2 py-0.5 text-xs text-blue-600 hover:underline dark:text-blue-400">
                <svg className="h-3 w-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" strokeLinecap="round" strokeLinejoin="round"/>
                  <polyline points="22,6 12,13 2,6" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
                {email}
              </a>
            )}
          </div>
        )}

        {/* Open full detail */}
        <div className="border-t border-gray-100 px-3 py-1.5 dark:border-gray-800">
          <button
            onClick={() => window.open(`/core/contacts/detail/${contactId}`, '_blank')}
            className="w-full text-center text-[11px] text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
          >
            Open Full Contact
          </button>
        </div>
      </div>
    </>
  );
}

export default withDevIdentifier(ContactCard, 'ContactCard', 'amber', 'apps/core/models/contact/pages/ContactCard.tsx');
