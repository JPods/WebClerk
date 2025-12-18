import * as z from "zod";
import { RefsForm, RefsApi } from "../types/contactType";
/* -----------------------------
   REF SCHEMAS
----------------------------- */

export const emailRefSchema = z.object({
  id: z.number(),
  name: z.string(),
  address: z.string().email(),
});

export const phoneRefSchema = z.object({
  id: z.number(),
  name: z.string(),
  number: z.string(),
});

export const locationRefSchema = z.object({
  id: z.number(),
});

/* -----------------------------
   REFS
----------------------------- */

export const refsSchema = z.object({
  tags: z.array(z.string()).default([]),
  categories: z.array(z.string()).default([]),
  keywords: z.array(z.string()).default([]),
  related_ids: z.array(z.string()).default([]),
  depends_on: z.record(z.any()).default({}),
  links: z
    .object({
      rep: z.array(z.string()).default([]),
      item: z.array(z.string()).default([]),
      email: z.array(emailRefSchema).default([]),
      phone: z.array(phoneRefSchema).default([]),
      order: z.array(z.string()).default([]),
      domain: z.array(z.string()).default([]),
      contact: z.array(z.string()).default([]),
      customer: z.array(z.string()).default([]),
      document: z.array(z.string()).default([]),
      location: z.array(locationRefSchema).default([]),
      manufacturer: z.array(z.string()).default([]),
      project: z.array(z.string()).default([]),
      vendor: z.array(z.string()).default([]),
    })
    .default({}),
});

/* -----------------------------
   CREATE
----------------------------- */

export const contactSchema = z
  .object({
    password: z.string().min(8),
    cnf_password: z.string(),
    email: z.string().email(),
    name_first: z.string().min(1),
    name_last: z.string().min(1),
    name_middle: z.string().optional(),
    name_prefix: z.string().optional(),
    name_suffix: z.string().optional(),
    role: z.string().optional(),
    company: z.string().optional(),
    title: z.string().optional(),
    department: z.string().optional(),
    is_active: z.boolean().default(false),
    is_staff: z.boolean().default(false),
    refs: refsSchema.optional(),
  })
  .refine((d) => d.password === d.cnf_password, {
    message: "Passwords do not match",
    path: ["cnf_password"],
  });

/* -----------------------------
   UPDATE
----------------------------- */

export const updateContactSchema = z
  .object({
    password: z.string().optional(),
    cnf_password: z.string().optional(),
    email: z.string().email(),
    name_first: z.string().min(1),
    name_last: z.string().min(1),
    name_middle: z.string().optional(),
    name_prefix: z.string().optional(),
    name_suffix: z.string().optional(),
    role: z.string().optional(),
    company: z.string().optional(),
    title: z.string().optional(),
    department: z.string().optional(),
    is_active: z.boolean().default(false),
    is_staff: z.boolean().default(false),
    refs: refsSchema.optional(),
  })
  .refine(
    (d) =>
      !d.password && !d.cnf_password ? true : d.password === d.cnf_password,
    {
      message: "Passwords do not match",
      path: ["cnf_password"],
    }
  );

export const mapRefsFormToApi = (refs: RefsForm): RefsApi => ({
  tags: refs.tags,
  categories: refs.categories,
  keywords: refs.keywords,
  related_ids: refs.related_ids,
  depends_on: refs.depends_on,
  links: {
    rep: refs.links.rep,
    item: refs.links.item,
    email: refs.links.email.map((e) => {
      return { id: e.id, name: e.name, address: e.address };
    }),
    phone: refs.links.phone.map((p) => {
      return { id: p.id, name: p.name, number: p.number };
    }),
    order: refs.links.order,
    domain: refs.links.domain,
    contact: refs.links.contact,
    customer: refs.links.customer,
    document: refs.links.document,
    location: refs.links.location.map((l) => {
      return { id: l.id };
    }),
    manufacturer: refs.links.manufacturer,
    project: refs.links.project,
    vendor: refs.links.vendor,
  },
});
