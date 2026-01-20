import * as z from "zod";

export const domainSchema = z.object({
  path: z.string().min(1, "Path is required"),
  type: z.string().min(1, "Type is required"),
});

export const updateDomainSchema = z.object({
  path: z.string().min(1, "First name is required"),
  type: z.string().min(1, "Last name is required"),
});

//  comment: z.string().optional(),
//   refs: z.string().optional(),
//   prefs: z.string().optional(),
//   metadata: z.string().optional(),
//   status: z.string().default("active"),
