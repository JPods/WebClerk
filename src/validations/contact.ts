import * as z from "zod";

export const contactSchema = z.object({
  prefix: z.string().optional(),
  name_first: z.string().min(1, "First name is required"),
  name_last: z.string().min(1, "Last name is required"),
  name_middle: z.string().optional(),
  attention: z.string().optional(),
  //rank: z.string().optional(),
  date_joined: z.string().optional(),
  role: z.string().optional(),
  company: z.string().optional(),
  phoneNumbers: z.array(
    z.object({
      format: z.string().min(1, "Phone format is required"),
      country_code: z.string().min(1, "Country code is required"),
      number: z
        .string()
        .min(1, "Phone number is required")
        .regex(/^\d+$/, "Phone number must contain only digits"),
    })
  ).min(1, "At least one phone number is required"),
  emails: z.array(
    z.object({
      type: z.string().min(1, "Email type is required"),
      email: z.string().email("Invalid email address"),
    })
  ).min(1, "At least one email is required"),
 });

 export const addressSchema = z.object({
   addresses: z.array(
      z.object({
        country: z.string().min(1, "Country is required"),
        state: z.string().min(1, "State is required"),
        zip: z.string().min(1, "Zip is required"),
        address1: z.string().min(1, "Street address is required"),
      })
    )
    .min(1, "At least one address is required"),
    domains: z.array(
      z.object({
        path: z.string().min(1, "Country is required"),
        type: z.string().min(1, "State is required"),
        comment: z.string().min(1, "Pincode is required"),
      })
    )
 })