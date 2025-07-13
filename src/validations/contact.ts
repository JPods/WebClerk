import * as z from "zod";

export const contactSchema = z.object({
  firstName: z.string().min(1, "First name is required"),
  lastName: z.string().min(1, "Last name is required"),
  companyName: z.string().min(1, "Company name is required"),
  role: z.string().min(1, "Role is required"),
  phoneNumbers: z.array(
    z.object({
      type: z.string().min(1, "Phone type is required"),
      countryCode: z.string().min(1, "Country code is required"),
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
  addresses: z
    .array(
      z.object({
        country: z.string().min(1, "Country is required"),
        state: z.string().min(1, "State is required"),
        pincode: z.string().min(1, "Pincode is required"),
        streetAddress: z.string().min(1, "Street address is required"),
      })
    )
    .min(1, "At least one address is required"),
 });