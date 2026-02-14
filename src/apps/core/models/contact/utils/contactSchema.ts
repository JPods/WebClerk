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

export const addressRefSchema = z.object({
  id: z.number(),
  name: z.string().default(""),
  address: z.string().default(""),
});

/* -----------------------------
   REFS
   The refs object is semi-structured: the API may return extra keys or
   object-typed entries in link arrays (e.g. customer:[{id,name}]).
   We keep validation loose here — mapping to the API payload shape
   happens in mapRefsFormToApi().
----------------------------- */

export const refsSchema = z.object({
  tags: z.array(z.any()).default([]),
  categories: z.array(z.any()).default([]),
  keywords: z.array(z.any()).default([]),
  related_ids: z.array(z.any()).default([]),
  depends_on: z.record(z.any()).default({}),
  links: z
    .object({
      rep: z.array(z.any()).default([]),
      item: z.array(z.any()).default([]),
      email: z.array(z.any()).default([]),
      phone: z.array(z.any()).default([]),
      order: z.array(z.any()).default([]),
      domain: z.array(z.any()).default([]),
      contact: z.array(z.any()).default([]),
      customer: z.array(z.any()).default([]),
      document: z.array(z.any()).default([]),
      address: z.array(z.any()).default([]),
      manufacturer: z.array(z.any()).default([]),
      project: z.array(z.any()).default([]),
      vendor: z.array(z.any()).default([]),
    })
    .passthrough()
    .default({}),
}).passthrough();

/* -----------------------------
   CREATE
----------------------------- */

/* Helper: valueAsNumber returns NaN for empty inputs — normalise to undefined */
const optionalNumber = z.preprocess(
  (v) => (v === "" || v === null || (typeof v === "number" && isNaN(v)) ? undefined : v),
  z.number().optional(),
);

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
    attention: z.string().optional(),
    role: z.string().optional(),
    company: z.string().optional(),
    title: z.string().optional(),
    department: z.string().optional(),
    customer_id: optionalNumber,
    rep_id: optionalNumber,
    vendor_id: optionalNumber,
    employee_id: optionalNumber,
    manufacturer_id: optionalNumber,
    other_id: optionalNumber,
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

export const updateContactSchema = z.object({
  email: z.string().email(),
  name_first: z.string().min(1),
  name_last: z.string().min(1),
  name_middle: z.string().optional(),
  name_prefix: z.string().optional(),
  name_suffix: z.string().optional(),
  attention: z.string().optional(),
  role: z.string().optional(),
  company: z.string().optional(),
  title: z.string().optional(),
  department: z.string().optional(),
  customer_id: optionalNumber,
  rep_id: optionalNumber,
  vendor_id: optionalNumber,
  employee_id: optionalNumber,
  manufacturer_id: optionalNumber,
  other_id: optionalNumber,
  is_active: z.boolean().default(false),
  is_staff: z.boolean().default(false),
  refs: refsSchema.optional(),
});

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
    address: refs.links.address.map((l) => {
      return { id: l.id, name: l.name, address: l.address };
    }),
    manufacturer: refs.links.manufacturer,
    project: refs.links.project,
    vendor: refs.links.vendor,
  },
});
