/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
/**
 * useDefaultCompany Hook
 * Fetches company branding from primary_organization (db_defaults)
 * and resolves canonical org details for print documents.
 */
import { useState, useEffect, useCallback, useRef } from 'react';
import { getRecords } from '@/api/wcapi';
import { orgApi } from '@/apps/orgs/services/orgApi';
import type { Organization } from '@/apps/orgs/types/orgTypes';

export interface CompanyInfo {
  id: number;
  name: string;
  attention?: string;
  phone: string;
  phoneCell?: string;
  fax?: string;
  email: string;
  domain?: string;
  website?: string;
  address: {
    line1: string;
    line2?: string;
    city: string;
    state: string;
    zip: string;
    country?: string;
  };
  logoUrl?: string;
}

interface UseDefaultCompanyResult {
  company: CompanyInfo | null;
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

interface PrimaryOrganizationSetting {
  id: number;
  config?: Record<string, any>;
  refs?: Record<string, any>;
}

const firstResult = <T,>(payload: any): T | undefined => {
  if (!payload) return undefined;
  if (Array.isArray(payload.results) && payload.results.length > 0) {
    return payload.results[0] as T;
  }
  if (payload.record && typeof payload.record === 'object') {
    return payload.record as T;
  }
  if (typeof payload === 'object' && payload !== null && ('id' in payload)) {
    return payload as T;
  }
  return undefined;
};

const toString = (...values: Array<unknown>): string => {
  for (const value of values) {
    if (typeof value === 'string' && value.trim()) return value.trim();
  }
  return '';
};

const toNumber = (value: unknown): number | null => {
  if (typeof value === 'number' && Number.isFinite(value)) return value;
  if (typeof value === 'string' && value.trim()) {
    const n = Number(value);
    if (Number.isFinite(n)) return n;
  }
  return null;
};

const pickBestPrimarySetting = (payload: any): PrimaryOrganizationSetting | undefined => {
  const rows: PrimaryOrganizationSetting[] = Array.isArray(payload?.results)
    ? payload.results
    : [];

  if (!rows.length) {
    return firstResult<PrimaryOrganizationSetting>(payload);
  }

  const withOrgId = rows
    .filter((row) => toNumber(row?.config?.org_id))
    .sort((a, b) => (Number(b?.id || 0) - Number(a?.id || 0)));

  if (withOrgId.length) return withOrgId[0];

  return rows.sort((a, b) => (Number(b?.id || 0) - Number(a?.id || 0)))[0];
};

const extractOrgIdFromSettingRefs = (setting?: PrimaryOrganizationSetting): number | null => {
  const links = (setting?.refs as any)?.links;
  if (!links || typeof links !== 'object') return null;

  const customer = (links as any).customer;
  if (Array.isArray(customer) && customer.length > 0) {
    const first = customer[0];
    if (typeof first === 'number' || typeof first === 'string') return toNumber(first);
    if (first && typeof first === 'object') return toNumber((first as any).id);
  }

  if (customer && typeof customer === 'object') {
    return toNumber((customer as any).id);
  }

  return null;
};

const normalizeWebsite = (domain: string): string | undefined => {
  if (!domain) return undefined;
  const clean = domain.replace(/^https?:\/\//i, '').trim();
  return clean ? `https://${clean}` : undefined;
};

const hasMeaningfulCompanyData = (company: CompanyInfo | null): boolean => {
  if (!company) return false;
  return Boolean(
    company.phone ||
      company.email ||
      company.address?.line1 ||
      company.address?.city,
  );
};

const extractOrgFromPayload = (payload: any): Organization | null => {
  const record = firstResult<Organization>(payload);
  if (record && (record as any).id) return record;
  return null;
};

const sleep = (ms: number): Promise<void> =>
  new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });

const getRecordsWithRetry = async (
  modelName: string,
  params: Record<string, any>,
  options?: { cacheExempt?: 'default-company' },
  maxAttempts = 4,
): Promise<any> => {
  let attempt = 0;
  while (attempt < maxAttempts) {
    try {
      return await getRecords(modelName, params, options);
    } catch (err: any) {
      attempt += 1;
      const status = err?.response?.status;
      const shouldRetry = status === 429 && attempt < maxAttempts;
      if (!shouldRetry) throw err;
      await sleep(250 * attempt);
    }
  }
  return null;
};

const toArray = <T,>(value: unknown): T[] => {
  if (Array.isArray(value)) return value as T[];
  if (value && typeof value === 'object') return [value as T];
  return [];
};

// Extract company info from Organization record
const extractCompanyInfo = (
  org: Organization,
  primaryData?: Record<string, any>,
): CompanyInfo => {
  const refsLinks = (org as any)?.refs?.links || {};
  const refsCustomer = Array.isArray(refsLinks.customer)
    ? refsLinks.customer[0]
    : refsLinks.customer;
  const refsContacts = Array.isArray(refsLinks.contact) ? refsLinks.contact : [];
  const billToContact =
    refsContacts.find((c: any) => c?.purpose === 'billto') || refsContacts[0] || {};

  const addresses = toArray<any>((org as any).addresses);
  const domains = toArray<any>((org as any).domains);
  const phones = toArray<any>((org as any).phones);
  const emails = toArray<any>((org as any).emails);

  // Get primary address from addresses array
  const primaryAddress = addresses.find(a => a?.type === 'primary') || addresses[0];
  
  // Get website from domains
  const primaryDomain =
    toString(
      domains.find(d => d?.verified)?.domain,
      domains[0]?.domain,
      (org as any).domain,
      (org as any).path,
      billToContact?.domain,
      refsCustomer?.domain,
      primaryData?.domain,
      primaryData?.company_domain,
      primaryData?.website,
    );
  
  // Get phone from phones array or top-level phone
  const primaryPhone =
    toString(
      phones.find(p => p?.primary)?.number,
      phones[0]?.number,
      org.phone,
      billToContact?.phone,
      refsCustomer?.phone,
      primaryData?.phone,
    );
  const cellPhone = phones.find(p => p?.type === 'cell')?.number;
  const faxPhone = phones.find(p => p?.type === 'fax')?.number;
  
  // Get email from emails array or top-level email
  const primaryEmail =
    toString(
      emails.find(e => e?.primary)?.email,
      emails[0]?.email,
      org.email,
      billToContact?.email,
      refsCustomer?.email,
      primaryData?.email,
    );
  
  // Get logo from connections or data
  const logoUrl =
    toString(
      org.connections?.logo_url,
      (org.data as Record<string, unknown>)?.logo_url as string,
      primaryData?.logo_url,
      primaryData?.logo,
    ) || undefined;

  const addressLine1 =
    toString(
      primaryAddress?.address?.line1,
      billToContact?.address_full,
      refsCustomer?.address_full,
      (org as any).address_full,
      primaryData?.address1,
      primaryData?.address,
    );

  const addressLine2 =
    toString(
      primaryAddress?.address?.line2,
      primaryData?.address2,
    ) || undefined;

  const city = toString(primaryAddress?.address?.city, billToContact?.city, refsCustomer?.city, primaryData?.city);
  const state = toString(primaryAddress?.address?.state, billToContact?.state, refsCustomer?.state, primaryData?.state);
  const zip = toString(primaryAddress?.address?.postal, billToContact?.zip, refsCustomer?.zip, primaryData?.zip);
  const country = toString(primaryAddress?.address?.country, billToContact?.country, refsCustomer?.country, primaryData?.country) || undefined;

  const attention =
    toString(
      primaryData?.attention,
      billToContact?.display_name,
      (org as any).attention,
    ) || undefined;

  return {
    id: org.id,
    name: toString(primaryData?.display_name, primaryData?.company, org.display_name, org.company),
    attention,
    phone: primaryPhone,
    phoneCell: cellPhone,
    fax: faxPhone,
    email: primaryEmail,
    domain: primaryDomain || undefined,
    website: normalizeWebsite(primaryDomain),
    address: {
      line1: addressLine1,
      line2: addressLine2,
      city,
      state,
      zip,
      country,
    },
    logoUrl,
  };
};

// Cache the company info to avoid repeated fetches
const STORAGE_KEY = 'wc3.defaultCompany.v1';

const readStoredCompany = (): { company: CompanyInfo | null; ts: number } => {
  if (typeof window === 'undefined') return { company: null, ts: 0 };
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return { company: null, ts: 0 };
    const parsed = JSON.parse(raw) as { company?: CompanyInfo; ts?: number };
    return {
      company: parsed?.company || null,
      ts: typeof parsed?.ts === 'number' ? parsed.ts : 0,
    };
  } catch {
    return { company: null, ts: 0 };
  }
};

const persistStoredCompany = (company: CompanyInfo, ts: number): void => {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify({ company, ts }));
  } catch {
    // Ignore storage errors; in-memory cache still works.
  }
};

const stored = readStoredCompany();
let cachedCompany: CompanyInfo | null = hasMeaningfulCompanyData(stored.company) ? stored.company : null;
let cacheTimestamp = hasMeaningfulCompanyData(stored.company) ? stored.ts : 0;
const CACHE_TTL = 5 * 60 * 1000; // 5 minutes
let inFlightCompanyFetch: Promise<CompanyInfo | null> | null = null;
let lastFailureAt = 0;
const FAILURE_COOLDOWN_MS = 10 * 1000;

export function useDefaultCompany(): UseDefaultCompanyResult {
  const [company, setCompany] = useState<CompanyInfo | null>(cachedCompany);
  const [loading, setLoading] = useState(!cachedCompany);
  const [error, setError] = useState<string | null>(null);
  const retryCountRef = useRef(0);
  const retryTimerRef = useRef<number | null>(null);

  const fetchCompany = useCallback(async () => {
    // Check cache validity
    const now = Date.now();
    if (
      cachedCompany &&
      hasMeaningfulCompanyData(cachedCompany) &&
      (now - cacheTimestamp) < CACHE_TTL
    ) {
      setCompany(cachedCompany);
      setLoading(false);
      return;
    }

    if (!cachedCompany && lastFailureAt && (now - lastFailureAt) < FAILURE_COOLDOWN_MS) {
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);

    // Reuse an ongoing startup/company fetch across all hook instances.
    if (inFlightCompanyFetch) {
      try {
        const shared = await inFlightCompanyFetch;
        if (shared) {
          setCompany(shared);
          return;
        }
      } catch {
        // Fall through to start a fresh fetch.
      }
    }

    const loadCompany = async (): Promise<CompanyInfo | null> => {
      // Primary source: singleton setting (purpose=db_defaults, name=primary_organization)
      const settingsData: any = await getRecordsWithRetry('setting', {
        purpose: 'db_defaults',
        name: 'primary_organization',
        is_active: true,
        limit: 1,
      }, { cacheExempt: 'default-company' });

      const setting: PrimaryOrganizationSetting | undefined = pickBestPrimarySetting(settingsData);
      const primaryData = setting?.config || {};
      const orgId =
        toNumber(primaryData?.org_id) ??
        toNumber(primaryData?.id) ??
        extractOrgIdFromSettingRefs(setting);
      const modelName =
        toString(primaryData?.model_name, primaryData?.org_type) || 'customer';

      if (orgId && modelName) {
        // Canonical path: use the setting's model_name and id exactly.
        let org: Organization | null = null;

        // Prefer list-form wcapi/get because it consistently returns full records.
        try {
          const listPayload: any = await getRecordsWithRetry(
            modelName,
            { id: orgId, limit: 1 },
            { cacheExempt: 'default-company' },
          );
          org = extractOrgFromPayload(listPayload);
        } catch {
          // Fall through to detail fetch.
        }

        if (!org || !org.id) {
          try {
            const detailPayload: any = await orgApi.get(orgId, modelName as any);
            org = extractOrgFromPayload(detailPayload) || ((detailPayload && detailPayload.id) ? detailPayload as Organization : null);
          } catch {
            // Keep org as null and continue to fallback section.
          }
        }

        if (org && org.id) {
          let companyInfo = extractCompanyInfo(org, primaryData);

          // Some list payloads are intentionally thin. If branding/contact
          // fields are sparse, force a detail fetch before accepting the result.
          if (!hasMeaningfulCompanyData(companyInfo)) {
            try {
              const detailPayload: any = await orgApi.get(orgId, modelName as any);
              const detailOrg =
                extractOrgFromPayload(detailPayload) ||
                ((detailPayload && detailPayload.id) ? (detailPayload as Organization) : null);
              if (detailOrg && detailOrg.id) {
                companyInfo = extractCompanyInfo(detailOrg, primaryData);
              }
            } catch {
              // Ignore and continue with best available companyInfo.
            }
          }

          if (hasMeaningfulCompanyData(companyInfo)) {
            cachedCompany = companyInfo;
            cacheTimestamp = now;
            persistStoredCompany(companyInfo, now);
            return companyInfo;
          }

          if (cachedCompany && hasMeaningfulCompanyData(cachedCompany)) {
            return cachedCompany;
          }

          // Return thin payload only when nothing better exists yet.
          return companyInfo;
        }
      }

      // Do not fan out to legacy default_company query path; keep startup load deterministic.
      return null;
    };

    try {
      inFlightCompanyFetch = loadCompany();
      const companyInfo = await inFlightCompanyFetch;

      if (companyInfo) {
        setCompany(companyInfo);
        retryCountRef.current = 0;
        lastFailureAt = 0;
      } else {
        setError('Primary organization/default company not configured');
        lastFailureAt = Date.now();
      }
    } catch (err) {
      console.error('Failed to fetch default company:', err);
      if (cachedCompany && hasMeaningfulCompanyData(cachedCompany)) {
        setCompany(cachedCompany);
      }
      setError(err instanceof Error ? err.message : 'Failed to fetch company');
      lastFailureAt = Date.now();

      // No retry. Fail visibly. User can reload if needed.
    } finally {
      inFlightCompanyFetch = null;
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchCompany();
    return () => {
      if (retryTimerRef.current) {
        window.clearTimeout(retryTimerRef.current);
      }
    };
  }, [fetchCompany]);

  return {
    company,
    loading,
    error,
    refetch: fetchCompany,
  };
}

// Export a function to clear cache (useful after company settings change)
export function clearDefaultCompanyCache(): void {
  cachedCompany = null;
  cacheTimestamp = 0;
  if (typeof window !== 'undefined') {
    try {
      window.localStorage.removeItem(STORAGE_KEY);
    } catch {
      // no-op
    }
  }
}

export default useDefaultCompany;
