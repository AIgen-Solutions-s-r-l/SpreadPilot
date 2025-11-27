import { z } from 'zod';

export const TradeSideSchema = z.enum(['BUY', 'SELL', 'LONG', 'SHORT']);
export const TradeStatusSchema = z.enum([
  'PENDING',
  'SUBMITTED',
  'FILLED',
  'PARTIAL',
  'CANCELLED',
  'REJECTED',
  'FAILED'
]);

export const TradeSchema = z.object({
  _id: z.string().optional(),
  id: z.string().optional(),
  follower_id: z.string(),
  side: TradeSideSchema,
  qty: z.number(),
  strike: z.number().optional(),
  symbol: z.string().optional(),
  status: TradeStatusSchema,
  limit_price_requested: z.number().optional(),
  fill_price: z.number().optional(),
  filled_qty: z.number().optional(),
  commission: z.number().optional(),
  timestamps: z.record(z.string(), z.string().or(z.date()).nullable()).optional(),
  error: z.string().optional(),
});

export type Trade = z.infer<typeof TradeSchema>;
