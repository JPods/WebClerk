"use client";

import type React from "react";
import { createContext, useContext, useEffect, useState, useCallback, useMemo } from "react";
import { getRecords } from "../api/wcapi";

/**
 * Badge preferences stored in contact.prefs.badge
 */
export interface BadgePrefs {
  bg_color?: string;     // hex color for badge background
  text_color?: string;   // hex color for badge text
  initials?: string;     // custom initials override
}

interface StaffContact {
  id: number;
  name_first?: string;
  name_last?: string;
  attention?: string;
  is_staff?: boolean;
  prefs?: {
    badge?: BadgePrefs;
    [key: string]: unknown;
  };
}

interface StaffBadgePrefsContextType {
  /** Map of contact ID to their badge prefs */
  badgePrefsMap: Map<number, BadgePrefs>;
  /** Get badge prefs for a specific contact ID */
  getBadgePrefs: (contactId: number | string) => BadgePrefs | undefined;
  /** Whether the initial fetch is still loading */
  isLoading: boolean;
  /** Refresh staff badge prefs from the API */
  refresh: () => Promise<void>;
}

const StaffBadgePrefsContext = createContext<StaffBadgePrefsContextType | undefined>(undefined);

export const StaffBadgePrefsProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const [badgePrefsMap, setBadgePrefsMap] = useState<Map<number, BadgePrefs>>(new Map());
  const [isLoading, setIsLoading] = useState(true);

  const fetchStaffBadgePrefs = useCallback(async () => {
    try {
      setIsLoading(true);
      // Fetch all staff contacts with their prefs
      const response = await getRecords("contact", {
        is_staff: true,
        limit: 500, // Should be more than enough for most organizations
      });

      const rawContacts = (response as any)?.records || response;
      const contacts: StaffContact[] = Array.isArray(rawContacts) ? rawContacts : [];
      const prefsMap = new Map<number, BadgePrefs>();

      for (const contact of contacts) {
        if (contact?.id && contact?.prefs?.badge) {
          prefsMap.set(contact.id, contact.prefs.badge);
        }
      }

      setBadgePrefsMap(prefsMap);
    } catch (error) {
      console.error("Failed to fetch staff badge prefs:", error);
      // Keep existing prefs on error
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Fetch on mount
  useEffect(() => {
    fetchStaffBadgePrefs();
  }, [fetchStaffBadgePrefs]);

  const getBadgePrefs = useCallback(
    (contactId: number | string): BadgePrefs | undefined => {
      const id = typeof contactId === "string" ? parseInt(contactId, 10) : contactId;
      if (Number.isNaN(id)) return undefined;
      return badgePrefsMap.get(id);
    },
    [badgePrefsMap]
  );

  const value = useMemo(
    () => ({
      badgePrefsMap,
      getBadgePrefs,
      isLoading,
      refresh: fetchStaffBadgePrefs,
    }),
    [badgePrefsMap, getBadgePrefs, isLoading, fetchStaffBadgePrefs]
  );

  return (
    <StaffBadgePrefsContext.Provider value={value}>
      {children}
    </StaffBadgePrefsContext.Provider>
  );
};

/**
 * Hook to access staff badge preferences
 * Must be used within a StaffBadgePrefsProvider
 */
export const useStaffBadgePrefs = () => {
  const context = useContext(StaffBadgePrefsContext);
  if (context === undefined) {
    throw new Error("useStaffBadgePrefs must be used within a StaffBadgePrefsProvider");
  }
  return context;
};

/**
 * Optional hook that returns undefined instead of throwing if used outside provider
 * Useful for components that may or may not have access to the context
 */
export const useStaffBadgePrefsOptional = () => {
  return useContext(StaffBadgePrefsContext);
};
