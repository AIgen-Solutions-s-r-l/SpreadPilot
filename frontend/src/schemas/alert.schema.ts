import { z } from 'zod';

export const AlertSeveritySchema = z.enum(['INFO', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL']);
export const AlertTypeSchema = z.string();

export const AlertSchema = z.object({
  _id: z.string().optional(),
  id: z.string().optional(),
  follower_id: z.string().optional().nullable(),
  severity: AlertSeveritySchema,
  type: AlertTypeSchema,
  message: z.string(),
  timestamp: z.number().or(z.string()).or(z.date()),
  acknowledged: z.boolean().optional(),
  acknowledged_at: z.string().or(z.date()).optional().nullable(),
  acknowledged_by: z.string().optional().nullable(),
});

export type Alert = z.infer<typeof AlertSchema>;
