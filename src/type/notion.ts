/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
export interface NotionSummary {
  totalItems: number;
  completedItems: number;
  inProgressItems: number;
  blockedItems?: number;
  completionRate: number;
  streakDays?: number;
  lastSynced?: string;
  activeModules?: number;
  upcomingDueCount?: number;
}

export interface NotionModule {
  id: string;
  title: string;
  status: string;
  percentComplete: number;
  lastUpdated?: string;
  dueDate?: string;
  tags?: string[];
  owner?: string;
  notionUrl?: string;
  description?: string;
}

export interface NotionTimelineEvent {
  id: string;
  title: string;
  date: string;
  status?: string;
  description?: string;
  icon?: string;
  percentComplete?: number;
}

export interface NotionResource {
  id: string;
  title: string;
  url: string;
  type?: string;
  status?: string;
  tagColor?: string;
  description?: string;
}

export interface NotionProgressResponse {
  summary: NotionSummary;
  modules: NotionModule[];
  timeline: NotionTimelineEvent[];
  resources: NotionResource[];
  trackings?: Array<{ label: string; value: number; target?: number }>;
}

export interface NotionModuleUpdatePayload {
  status?: string;
  percentComplete?: number;
  notes?: string;
}

export interface NotionAuthStatus {
  connected: boolean;
  lastSynced?: string;
  lastAttempt?: string;
  message?: string;
}
