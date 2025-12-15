import * as z from "zod";

export const employeeSchema = z.object({
  name: z.string().min(1, "Name is required"),
  employee_id: z.string().min(1, "Employee ID is required"),
  email: z.string().email("Invalid email"),
  phone: z.string().min(1, "Phone is required"),
  hire_date: z.string().min(1, "Hire date is required"),
  department: z.string().min(1, "Department is required"),
});