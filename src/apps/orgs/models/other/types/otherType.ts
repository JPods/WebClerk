/**
 * Other Org Types — matches wc3 OrgBase (org_type="other")
 * @see webClerk3/apps/orgs/models/base.py
 */

import type { Organization } from "@/apps/orgs/types/orgTypes";

export type OtherType = Organization & { org_type: "other" };