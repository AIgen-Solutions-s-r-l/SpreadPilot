import { z } from 'zod';

// Follower P&L item schema (new format from PostgreSQL)
export const FollowerPnlSchema = z.object({
  follower_id: z.string(),
  pnl: z.number(),
});

// Array of follower P&L items
export const FollowerPnlArraySchema = z.array(FollowerPnlSchema);

// Legacy Daily P&L schema (for backward compatibility)
export const DailyPnlSchema = z.object({
  date: z.string(),
  total_pnl: z.number(),
  realized_pnl: z.number(),
  unrealized_pnl: z.number(),
  trades: z.array(z.object({
    symbol: z.string(),
    pnl: z.number(),
    quantity: z.number(),
  })).optional(),
  message: z.string().optional(),
});

// Legacy Monthly P&L schema (for backward compatibility)
export const MonthlyPnlSchema = z.object({
  year: z.number(),
  month: z.number(),
  total_pnl: z.number(),
  realized_pnl: z.number(),
  unrealized_pnl: z.number(),
  daily_breakdown: z.array(DailyPnlSchema),
  days_with_data: z.number(),
});

// Type exports
export type FollowerPnl = z.infer<typeof FollowerPnlSchema>;
export type FollowerPnlArray = z.infer<typeof FollowerPnlArraySchema>;
export type DailyPnl = z.infer<typeof DailyPnlSchema>;
export type MonthlyPnl = z.infer<typeof MonthlyPnlSchema>;