import { z } from 'zod';

// Log level schema
export const LogLevelSchema = z.enum(['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']);

// Log entry schema
export const LogEntrySchema = z.object({
  timestamp: z.string().transform((val) => new Date(val)),
  service: z.string(),
  level: LogLevelSchema,
  message: z.string(),
  extra: z.record(z.any()).optional(),
});

// Logs response schema
export const LogsResponseSchema = z.object({
  count: z.number(),
  requested: z.number(),
  filters: z.object({
    service: z.string().nullable(),
    level: z.string().nullable(),
    search: z.string().nullable(),
  }),
  logs: z.array(LogEntrySchema),
});

// Type exports
export type LogLevel = z.infer<typeof LogLevelSchema>;
export type LogEntry = z.infer<typeof LogEntrySchema>;
export type LogsResponse = z.infer<typeof LogsResponseSchema>;