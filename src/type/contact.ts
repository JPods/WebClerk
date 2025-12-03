export interface CreateContactRequest {
  name_first: string;
  name_last: string;
  name_middle: string;
  email: string;
  phone: string;
  company?: string;
  name_suffix?: string;
  name_prefix?: string;
  title?: string;
  department?: string;
  comment?: string;
  role?: string;
}
export interface ContactApiTask {
  name_first: string;
  name_last: string;
  name_middle: string;
  email: string;
  phone: string;
  company?: string;
  name_suffix?: string;
  name_prefix?: string;
  title?: string;
  department?: string;
  comment?: string;
  role?: string;
}
// export const contactSchema = z.object({
//   name_first: z.string().min(1, "First Name is required"),
//   name_last: z.string().min(1, "Last Name is required"),
//   name_middle: z.string().min(1, "Middle Name is required"),
//   email: z.string().min(1, "Email is required").email("Invalid email format"),
//   phone: z.string().min(1, "Phone is required"),
//   company: z.string().min(1, "Company is required"),
//   customer_id: z.string().min(1, "Customer ID is required"),
//   name_suffix: z.string().optional(),
//   name_prefix: z.string().optional(),
//   title: z.string().optional(),
//   department: z.string().optional(),
//   comment: z.string().optional(),
//   role: z.string().min(1, "Role is required"),
//   address1: z.string().optional(),
//   address2: z.string().optional(),
//   city: z.string().optional(),
//   state: z.string().optional(),
//   zip: z.string().optional(),
//   country: z.string().optional(),
//   fax: z.string().optional(),
//   profile1: z.string().optional(),
//   profile2: z.string().optional(),
//   profile3: z.string().optional(),
//   profile4: z.string().optional(),
//   profile5: z.string().optional(),
//   rep_id: z.string().optional(),
//   sales_id: z.string().optional(),
//   retired: z.boolean().optional(),
//   dt_retired: z.string().optional(),
//   unique_id: z.string().optional(),
//   ship_via: z.string().optional(),
//   zone: z.string().optional(),
//   tax_juris: z.string().optional(),
// });
