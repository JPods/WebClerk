import { z } from 'zod';

// Base login schema that can be extended
export const loginSchema = z.object({
  email: z.string()
    .min(1, 'Email is required'),
  password: z.string()
    .min(6, 'Password must be at least 6 char.')
    .max(32, 'Password must be less than 32 char.'),
  //rememberMe: z.boolean().optional(),
});

// Type for TypeScript
export type LoginFormData = z.infer<typeof loginSchema>;

// Register schema (extends login with additional fields)
export const registerSchema = loginSchema.extend({
    email:  z.string().min(1, 'Email is required'),
    name_first: z.string().min(1, 'First name is required'),  
    name_last: z.string().min(1, 'Last name is required'),
    role: z.string().min(1, 'Username is required'),
    confirmPassword: z.string().min(1, 'Please confirm your password'),
  })
  .refine(data => data.password === data.confirmPassword, {
  message: "Passwords don't match",
  path: ['confirmPassword'],
});

export type RegisterFormData = z.infer<typeof registerSchema>;