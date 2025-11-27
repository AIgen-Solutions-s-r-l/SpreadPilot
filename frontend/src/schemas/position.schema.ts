import { z } from 'zod';

export const PositionSchema = z.object({
  _id: z.string().optional(),
  id: z.string().optional(),
  follower_id: z.string(),
  symbol: z.string(),
  quantity: z.number(),
  avg_cost: z.number(),
  current_price: z.number().optional(),
  market_value: z.number().optional(),
  unrealized_pnl: z.number().optional(),
  realized_pnl: z.number().optional(),
  updated_at: z.string().or(z.date()),
});

export type Position = z.infer<typeof PositionSchema>;
