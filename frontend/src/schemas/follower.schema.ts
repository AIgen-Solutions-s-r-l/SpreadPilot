import { z } from 'zod';

// Enum schemas
export const BotStatusSchema = z.enum(['RUNNING', 'STOPPED', 'ERROR', 'STARTING']);
export const IbGwStatusSchema = z.enum(['CONNECTED', 'DISCONNECTED', 'CONNECTING', 'ERROR']);
export const AssignmentStateSchema = z.enum(['ASSIGNED', 'UNASSIGNED', 'PENDING']);

// Follower schema
export const FollowerSchema = z.object({
  id: z.string(),
  enabled: z.boolean(),
  botStatus: BotStatusSchema,
  ibGwStatus: IbGwStatusSchema,
  assignmentState: AssignmentStateSchema,
  pnlToday: z.number(),
  pnlMonth: z.number(),
  pnlTotal: z.number(),
  // Additional fields that might come from the API
  name: z.string().optional(),
  email: z.string().email().optional(),
  iban: z.string().optional(),
  commission_pct: z.number().optional(),
  timeValue: z.number().optional(), // For TV badge colors
});

// Array of followers
export const FollowersResponseSchema = z.array(FollowerSchema);

// Create follower request schema
export const CreateFollowerSchema = z.object({
  name: z.string().min(1, 'Name is required'),
  email: z.string().email('Invalid email address'),
  iban: z.string().min(1, 'IBAN is required'),
  commission_pct: z.number().min(0).max(100),
  enabled: z.boolean().default(true),
});

// Type exports
export type Follower = z.infer<typeof FollowerSchema>;
export type CreateFollowerRequest = z.infer<typeof CreateFollowerSchema>;