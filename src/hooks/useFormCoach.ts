/**
 * useFormCoach — Data-completeness coaching for transaction forms
 *
 * Validates a transaction record against configurable rules and returns
 * a list of issues grouped by severity:
 *   - "error"   (red)   — Required field is completely missing
 *   - "warning" (orange) — Field exists but data is incomplete or suspect
 *   - "info"    (blue)   — Suggestion for improvement
 *
 * The hook is triggered explicitly (e.g. before print) rather than on
 * every render, so it does not affect normal editing performance.
 *
 * Usage:
 *   const { issues, hasErrors, hasWarnings, runCheck } = useFormCoach(data, 'order');
 *   // Call runCheck() before print to populate issues
 */
import { useState, useCallback, useMemo } from 'react';

// ── Types ──────────────────────────────────────────────────────────────

export type CoachSeverity = 'error' | 'warning' | 'info';

export interface CoachIssue {
  /** Unique key for React rendering */
  key: string;
  /** Severity determines display color */
  severity: CoachSeverity;
  /** Human-readable label (e.g. "Bill-To Address") */
  field: string;
  /** Explanation shown to the user */
  message: string;
  /** Optional: which tab/section contains this field */
  section?: string;
}

export type TransactionModelType =
  | 'order'
  | 'invoice'
  | 'proposal'
  | 'purchase'
  | 'workorder'
  | 'receipt'
  | 'adjustment';

// ── Rule definition ────────────────────────────────────────────────────

interface CoachRule {
  key: string;
  field: string;
  section?: string;
  /** Which transaction types this rule applies to (empty = all) */
  models?: TransactionModelType[];
  /** Return a CoachIssue or null */
  check: (data: Record<string, unknown>) => Omit<CoachIssue, 'key' | 'field' | 'section'> | null;
}

// ── Helpers ────────────────────────────────────────────────────────────

const isEmpty = (v: unknown): boolean =>
  v === undefined || v === null || v === '' || v === 0;

const isBlankString = (v: unknown): boolean =>
  typeof v !== 'string' || v.trim() === '';

/** Dig into nested data using dot-delimited path */
const dig = (obj: Record<string, unknown>, path: string): unknown => {
  return path.split('.').reduce<unknown>((cur, key) => {
    if (cur && typeof cur === 'object') return (cur as Record<string, unknown>)[key];
    return undefined;
  }, obj);
};

/** Check if a contact with given purpose exists and has address fields */
const findContact = (data: Record<string, unknown>, purpose: string) => {
  const contacts = dig(data, 'refs.links.contact') as Array<Record<string, unknown>> | undefined;
  if (!Array.isArray(contacts)) return undefined;
  return contacts.find((c) => c.purpose === purpose);
};

/** Check a party block (contact or customer) for address completeness */
const hasAddress = (party: Record<string, unknown> | undefined): boolean => {
  if (!party) return false;
  // Address is present if address_full exists, or individual fields exist
  if (party.address_full && !isBlankString(party.address_full)) return true;
  if (party.address1 && !isBlankString(party.address1)) return true;
  return !!(party.city || party.state || party.zip);
};

// ── Default rules ──────────────────────────────────────────────────────

const COACH_RULES: CoachRule[] = [
  // ── Customer / Org ────────────────────────────────────────────────
  {
    key: 'customer_missing',
    field: 'Customer',
    section: 'Header',
    models: ['order', 'invoice', 'proposal'],
    check: (data) => {
      const cust = dig(data, 'refs.links.customer');
      const custId = data.customer_id;
      if (!cust && isEmpty(custId)) {
        return { severity: 'error', message: 'No customer assigned to this transaction' };
      }
      return null;
    },
  },

  // ── Bill-To ───────────────────────────────────────────────────────
  {
    key: 'billto_missing',
    field: 'Bill-To Contact',
    section: 'Contacts',
    models: ['order', 'invoice'],
    check: (data) => {
      const billto = findContact(data, 'billto');
      if (!billto) {
        return { severity: 'error', message: 'No bill-to contact assigned — required for printing' };
      }
      return null;
    },
  },
  {
    key: 'billto_no_address',
    field: 'Bill-To Address',
    section: 'Contacts',
    models: ['order', 'invoice'],
    check: (data) => {
      const billto = findContact(data, 'billto');
      if (billto && !hasAddress(billto)) {
        return { severity: 'warning', message: 'Bill-to contact has no address on file' };
      }
      return null;
    },
  },
  {
    key: 'billto_no_email',
    field: 'Bill-To Email',
    section: 'Contacts',
    models: ['order', 'invoice'],
    check: (data) => {
      const billto = findContact(data, 'billto');
      if (billto && isBlankString(billto.email)) {
        return { severity: 'warning', message: 'Bill-to contact has no email address' };
      }
      return null;
    },
  },
  {
    key: 'billto_no_phone',
    field: 'Bill-To Phone',
    section: 'Contacts',
    models: ['order', 'invoice'],
    check: (data) => {
      const billto = findContact(data, 'billto');
      if (billto && isBlankString(billto.phone)) {
        return { severity: 'info', message: 'Bill-to contact has no phone number' };
      }
      return null;
    },
  },

  // ── Ship-To ───────────────────────────────────────────────────────
  {
    key: 'shipto_missing',
    field: 'Ship-To Contact',
    section: 'Contacts',
    models: ['order', 'invoice'],
    check: (data) => {
      const shipto = findContact(data, 'shipto');
      if (!shipto) {
        return { severity: 'warning', message: 'No ship-to contact assigned' };
      }
      return null;
    },
  },
  {
    key: 'shipto_no_address',
    field: 'Ship-To Address',
    section: 'Contacts',
    models: ['order', 'invoice'],
    check: (data) => {
      const shipto = findContact(data, 'shipto');
      if (shipto && !hasAddress(shipto)) {
        return { severity: 'error', message: 'Ship-to contact has no shipping address' };
      }
      return null;
    },
  },

  // ── Vendor (purchases) ───────────────────────────────────────────
  {
    key: 'vendor_missing',
    field: 'Vendor',
    section: 'Header',
    models: ['purchase'],
    check: (data) => {
      const vendor = dig(data, 'refs.links.vendor');
      const vendorId = data.vendor_id;
      if (!vendor && isEmpty(vendorId)) {
        return { severity: 'error', message: 'No vendor assigned to this purchase' };
      }
      return null;
    },
  },

  // ── Lines ─────────────────────────────────────────────────────────
  {
    key: 'no_lines',
    field: 'Line Items',
    section: 'Lines',
    check: (data) => {
      const lines = data.lines as unknown[] | undefined;
      if (!lines || !Array.isArray(lines) || lines.length === 0) {
        return { severity: 'error', message: 'Transaction has no line items' };
      }
      return null;
    },
  },
  {
    key: 'lines_zero_price',
    field: 'Line Pricing',
    section: 'Lines',
    models: ['order', 'invoice', 'proposal'],
    check: (data) => {
      const lines = data.lines as Array<Record<string, unknown>> | undefined;
      if (!Array.isArray(lines)) return null;
      const zeroLines = lines.filter((l) => {
        const price = dig(l, 'price.unit') as number | undefined;
        return price === 0 || price === undefined || price === null;
      });
      if (zeroLines.length > 0) {
        return {
          severity: 'warning',
          message: `${zeroLines.length} line(s) have $0.00 unit price`,
        };
      }
      return null;
    },
  },

  // ── Terms & Dates ─────────────────────────────────────────────────
  {
    key: 'no_terms',
    field: 'Payment Terms',
    section: 'Header',
    models: ['order', 'invoice'],
    check: (data) => {
      if (isBlankString(data.terms)) {
        return { severity: 'warning', message: 'No payment terms set' };
      }
      return null;
    },
  },
  {
    key: 'no_due_date',
    field: 'Due Date',
    section: 'Header',
    models: ['order', 'invoice'],
    check: (data) => {
      if (isEmpty(data.due_date)) {
        return { severity: 'warning', message: 'No due date specified' };
      }
      return null;
    },
  },
  {
    key: 'no_po_number',
    field: 'PO Number',
    section: 'Header',
    models: ['order'],
    check: (data) => {
      if (isBlankString(data.po_number)) {
        return { severity: 'info', message: 'Customer PO number not entered' };
      }
      return null;
    },
  },

  // ── Totals ────────────────────────────────────────────────────────
  {
    key: 'zero_total',
    field: 'Total',
    section: 'Financials',
    check: (data) => {
      const total = dig(data, 'totals.total') as number | undefined;
      if (total === 0) {
        return { severity: 'warning', message: 'Transaction total is $0.00' };
      }
      return null;
    },
  },

  // ── Status ────────────────────────────────────────────────────────
  {
    key: 'status_planned',
    field: 'Status',
    section: 'Header',
    models: ['order', 'invoice'],
    check: (data) => {
      if (data.status === 'planned') {
        return { severity: 'info', message: 'Transaction is still in "planned" status' };
      }
      return null;
    },
  },
];

// ── Hook ───────────────────────────────────────────────────────────────

export interface UseFormCoachReturn {
  /** All issues from last check */
  issues: CoachIssue[];
  /** Errors only (red) */
  errors: CoachIssue[];
  /** Warnings only (orange) */
  warnings: CoachIssue[];
  /** Info only (blue) */
  infos: CoachIssue[];
  /** Quick boolean checks */
  hasErrors: boolean;
  hasWarnings: boolean;
  hasIssues: boolean;
  /** Run validation checks and return issues */
  runCheck: () => CoachIssue[];
  /** Clear all issues */
  clearIssues: () => void;
  /** Whether check has been run at least once */
  hasChecked: boolean;
}

export function useFormCoach(
  data: Record<string, unknown> | null | undefined,
  modelType: TransactionModelType,
  /** Pass custom rules to extend/override defaults */
  extraRules?: CoachRule[],
): UseFormCoachReturn {
  const [issues, setIssues] = useState<CoachIssue[]>([]);
  const [hasChecked, setHasChecked] = useState(false);

  const allRules = useMemo(
    () => [...COACH_RULES, ...(extraRules ?? [])],
    [extraRules],
  );

  const runCheck = useCallback((): CoachIssue[] => {
    if (!data) {
      setIssues([]);
      setHasChecked(true);
      return [];
    }

    const found: CoachIssue[] = [];

    for (const rule of allRules) {
      // Skip rules that don't apply to this model type
      if (rule.models && rule.models.length > 0 && !rule.models.includes(modelType)) {
        continue;
      }

      try {
        const result = rule.check(data);
        if (result) {
          found.push({
            key: rule.key,
            field: rule.field,
            section: rule.section,
            ...result,
          });
        }
      } catch {
        // Silently skip rules that throw
      }
    }

    // Sort: errors first, then warnings, then info
    const order: Record<CoachSeverity, number> = { error: 0, warning: 1, info: 2 };
    found.sort((a, b) => order[a.severity] - order[b.severity]);

    setIssues(found);
    setHasChecked(true);
    return found;
  }, [data, modelType, allRules]);

  const clearIssues = useCallback(() => {
    setIssues([]);
    setHasChecked(false);
  }, []);

  const errors = useMemo(() => issues.filter((i) => i.severity === 'error'), [issues]);
  const warnings = useMemo(() => issues.filter((i) => i.severity === 'warning'), [issues]);
  const infos = useMemo(() => issues.filter((i) => i.severity === 'info'), [issues]);

  return {
    issues,
    errors,
    warnings,
    infos,
    hasErrors: errors.length > 0,
    hasWarnings: warnings.length > 0,
    hasIssues: issues.length > 0,
    runCheck,
    clearIssues,
    hasChecked,
  };
}

export default useFormCoach;
