/**
 * useDefaultCompany Hook
 * Fetches the organization record with status = "DefaultCompany"
 * This record contains company branding info for print documents
 */
import { useState, useEffect, useCallback } from 'react';
import { orgApi } from '@/apps/orgs/services/orgApi';
import type { Organization } from '@/apps/orgs/types/orgTypes';

export interface CompanyInfo {
  id: number;
  name: string;
  phone: string;
  phoneCell?: string;
  fax?: string;
  email: string;
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

// Extract company info from Organization record
const extractCompanyInfo = (org: Organization): CompanyInfo => {
  // Get primary address from addresses array
  const primaryAddress = org.addresses?.find(a => a.type === 'primary') || org.addresses?.[0];
  
  // Get website from domains
  const primaryDomain = org.domains?.find(d => d.verified)?.domain || org.domains?.[0]?.domain;
  
  // Get phone from phones array or top-level phone
  const primaryPhone = org.phones?.find(p => p.primary)?.number || org.phones?.[0]?.number || org.phone || '';
  const cellPhone = org.phones?.find(p => p.type === 'cell')?.number;
  const faxPhone = org.phones?.find(p => p.type === 'fax')?.number;
  
  // Get email from emails array or top-level email
  const primaryEmail = org.emails?.find(e => e.primary)?.email || org.emails?.[0]?.email || org.email || '';
  
  // Get logo from connections or data
  const logoUrl = org.connections?.logo_url || (org.data as Record<string, unknown>)?.logo_url as string;

  return {
    id: org.id,
    name: org.display_name || org.company || '',
    phone: primaryPhone,
    phoneCell: cellPhone,
    fax: faxPhone,
    email: primaryEmail,
    website: primaryDomain ? `https://${primaryDomain}` : undefined,
    address: {
      line1: primaryAddress?.address?.line1 || '',
      line2: primaryAddress?.address?.line2,
      city: primaryAddress?.address?.city || '',
      state: primaryAddress?.address?.state || '',
      zip: primaryAddress?.address?.postal || '',
      country: primaryAddress?.address?.country,
    },
    logoUrl,
  };
};

// Cache the company info to avoid repeated fetches
let cachedCompany: CompanyInfo | null = null;
let cacheTimestamp = 0;
const CACHE_TTL = 5 * 60 * 1000; // 5 minutes

export function useDefaultCompany(): UseDefaultCompanyResult {
  const [company, setCompany] = useState<CompanyInfo | null>(cachedCompany);
  const [loading, setLoading] = useState(!cachedCompany);
  const [error, setError] = useState<string | null>(null);

  const fetchCompany = useCallback(async () => {
    // Check cache validity
    const now = Date.now();
    if (cachedCompany && (now - cacheTimestamp) < CACHE_TTL) {
      setCompany(cachedCompany);
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      // Fetch organization with status = "DefaultCompany"
      const response = await orgApi.list({
        status: 'default_company' as never,
        is_active: true,
        limit: 1,
      });

      if (response.results && response.results.length > 0) {
        const org = response.results[0];
        const companyInfo = extractCompanyInfo(org);
        
        // Update cache
        cachedCompany = companyInfo;
        cacheTimestamp = now;
        
        setCompany(companyInfo);
      } else {
        // Fallback: Try to find by name pattern or first active org
        console.warn('No DefaultCompany found, using fallback');
        setError('Default company not configured');
      }
    } catch (err) {
      console.error('Failed to fetch default company:', err);
      setError(err instanceof Error ? err.message : 'Failed to fetch company');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchCompany();
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
}

export default useDefaultCompany;
