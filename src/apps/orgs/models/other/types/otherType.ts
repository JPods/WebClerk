/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
/**
 * Other Org Types — matches wc3 OrgBase (org_type="other")
 * @see webClerk3/apps/orgs/models/base.py
 */

import type { Organization } from "@/apps/orgs/types/orgTypes";

export type OtherType = Organization & { org_type: "other" };