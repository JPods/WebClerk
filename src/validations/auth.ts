import { z } from 'zod';

// Base login schema that can be extended
export const loginSchema = z.object({
  username: z.string()
    .min(1, 'Username is required'),
  password: z.string()
    .min(6, 'Password must be at least 6 characters')
    .max(32, 'Password must be less than 32 characters'),
  //rememberMe: z.boolean().optional(),
});

// Type for TypeScript
export type LoginFormData = z.infer<typeof loginSchema>;

// Register schema (extends login with additional fields)
export const registerSchema = loginSchema.extend({
  username: z.string()
    .min(3, 'Username must be at least 3 characters')
    .max(20, 'Username must be less than 20 characters'),
  confirmPassword: z.string()
    .min(1, 'Please confirm your password'),
}).refine(data => data.password === data.confirmPassword, {
  message: "Passwords don't match",
  path: ['confirmPassword'],
});

export type RegisterFormData = z.infer<typeof registerSchema>;