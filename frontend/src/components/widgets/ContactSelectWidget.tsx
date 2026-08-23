/**
 * ContactSelectWidget — multi-contact picker with chips.
 *
 * assigned_to is an array of {id, name}. First entry is the Responsible Person.
 * Label-as-select: the field name IS the add-contact dropdown.
 * Chips below show assigned contacts — click name to open record.
 */
import { useState, useEffect, useCallback } from "react";
import type { WidgetProps } from "./types";
import { getRecords } from "../../api/wcapi";

const chipClass =
  "inline-flex items-center rounded-full bg-indigo-50 px-2 py-0.5 text-[10px] font-semibold text-indigo-700 ring-1 ring-indigo-200 dark:bg-indigo-500/10 dark:text-indigo-100 dark:ring-indigo-500/40";

type AssignEntry = { id?: number; name?: string };

function parseValue(value: any): AssignEntry[] {
  if (!value) return [];

  if (Array.isArray(value)) {
    return value.map(v =>
      typeof v === "string" ? { name: v } :
      (v && typeof v === "object") ? { id: v.id ? Number(v.id) : undefined, name: v.name || v.label } :
      { name: String(v) }
    ).filter(e => e.name);
  }

  if (typeof value === "string") {
    try {
      const parsed = JSON.parse(value.replace(/'/g, '"'));
      return parseValue(parsed);
    } catch {}
    return [{ name: value }];
  }

  // {lead, team} — old kanban format
  if (typeof value === "object" && value.lead) {
    const entries: AssignEntry[] = [{ name: value.lead }];
    if (Array.isArray(value.team)) {
      for (const t of value.team) {
        const n = typeof t === "string" ? t : t?.name;
        if (n && n !== value.lead) entries.push({ name: n });
      }
    }
    return entries;
  }

  if (typeof value === "object" && (value.id || value.name)) {
    return [{ id: value.id ? Number(value.id) : undefined, name: value.name }];
  }

  return [];
}

export const ContactSelectWidget: React.FC<WidgetProps> = ({
  name, value, onChange, disabled, mode, record,
}) => {
  const entries = parseValue(value);
  const [options, setOptions] = useState<{ id: string; label: string }[]>([]);

  useEffect(() => {
    (async () => {
      const seen = new Map<string, string>();

      // Source 1: is_staff contacts
      try {
        const res = await getRecords('contact', { is_staff: true, is_active: true, limit: 200 }) as any;
        for (const r of (res?.results || [])) {
          const label = r.attention || `${r.name_first || ''} ${r.name_last || ''}`.trim() || `Contact #${r.id}`;
          seen.set(String(r.id), label);
        }
      } catch {}

      // Source 2: active project prefs.assigned_to
      try {
        const projRes = await getRecords('project', { status__in: 'open,in_progress', limit: 5 }) as any;
        for (const proj of (projRes?.results || [])) {
          const arr = proj?.prefs?.assigned_to;
          if (Array.isArray(arr)) {
            for (const a of arr) {
              if (a.id && !seen.has(String(a.id))) {
                seen.set(String(a.id), a.name || a.label || `Contact #${a.id}`);
              }
            }
          }
        }
      } catch {}

      // Source 3: current record's prefs.assigned_to
      const recArr = record?.prefs?.assigned_to;
      if (Array.isArray(recArr)) {
        for (const a of recArr) {
          if (a.id && !seen.has(String(a.id))) {
            seen.set(String(a.id), a.name || a.label || `Contact #${a.id}`);
          }
        }
      }

      setOptions(Array.from(seen.entries()).map(([id, label]) => ({ id, label })));
    })();
  }, [record]);

  // Open a contact record — by id directly, by name search if no id
  const handleOpenContact = useCallback((e: AssignEntry) => {
    if (e.id) {
      window.open(`/contact/${e.id}`, '_blank');
    } else if (e.name) {
      // Legacy data without id — search by name
      getRecords('contact', { keyword: e.name, is_active: true, limit: 5 }).then((res: any) => {
        const matches = res?.results || [];
        if (matches.length >= 1) {
          window.open(`/contact/${matches[0].id}`, '_blank');
        } else {
          alert(`No active contact found for "${e.name}".`);
        }
      }).catch(() => { alert(`Could not search for "${e.name}".`); });
    }
  }, []);

  if (mode === "print") {
    return <span className="text-[inherit]">{entries.map(e => e.name).join(", ") || "—"}</span>;
  }

  // Shared chip renderer — click name opens contact, always clickable
  const renderChip = (e: AssignEntry, i: number, showRemove: boolean) => (
    <span key={e.id || e.name || i} className={chipClass}>
      {i === 0 && entries.length > 1 && <span title="Responsible Person" className="mr-1">★</span>}
      <span
        style={{ cursor: 'pointer', textDecoration: 'underline', textDecorationStyle: 'dotted' as const }}
        onClick={(ev) => { ev.stopPropagation(); handleOpenContact(e); }}
        title={`Open ${e.name || 'contact'} record`}
      >{e.name || `#${e.id}`}</span>
      {showRemove && (
        <button type="button" className="ml-1 text-indigo-500 hover:text-rose-500"
          onClick={(ev) => { ev.stopPropagation(); onChange(entries.filter((_, j) => j !== i)); }}>×</button>
      )}
    </span>
  );

  // Display mode
  if (disabled) {
    return (
      <div>
        <div className="font-mono text-[0.85em] mb-0.5 text-indigo-600 dark:text-indigo-400 font-semibold">{name}</div>
        <div className="flex flex-wrap gap-1 min-h-[20px]">
          {entries.length === 0 && <span className="text-gray-400 text-[inherit]">—</span>}
          {entries.map((e, i) => renderChip(e, i, false))}
        </div>
      </div>
    );
  }

  // Edit mode — label-as-select for adding, chips for current
  const add = (contactId: string) => {
    if (!contactId) return;
    const opt = options.find(o => o.id === contactId);
    if (!opt) return;
    if (entries.some(e => String(e.id) === contactId)) return;
    onChange([...entries, { id: Number(contactId), name: opt.label }]);
  };

  return (
    <div>
      <select
        name={name}
        value=""
        onChange={e => add(e.target.value)}
        className="font-mono text-[0.85em] mb-0.5 bg-transparent border-none cursor-pointer text-indigo-600 dark:text-indigo-400 font-semibold outline-none"
        style={{ fontSize: 'inherit', padding: 0 }}
      >
        <option value="">{name}</option>
        {options
          .filter(o => !entries.some(e => String(e.id) === o.id))
          .map(o => <option key={o.id} value={o.id}>{o.label}</option>)
        }
      </select>
      <div className="flex flex-wrap gap-1 min-h-[20px]">
        {entries.map((e, i) => renderChip(e, i, true))}
      </div>
    </div>
  );
};
