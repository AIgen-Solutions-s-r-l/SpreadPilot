import { z } from 'zod';

// Daily P&L schema
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

// Monthly P&L schema
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
export type DailyPnl = z.infer<typeof DailyPnlSchema>;
export type MonthlyPnl = z.infer<typeof MonthlyPnlSchema>;