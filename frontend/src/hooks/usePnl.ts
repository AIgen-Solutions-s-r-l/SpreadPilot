import { useState, useEffect, useCallback } from 'react';
import { getTodayPnl, getMonthlyPnl } from '../services/pnlService';
import type { DailyPnl, MonthlyPnl } from '../schemas/pnl.schema';

export const usePnl = () => {
  const [todayPnl, setTodayPnl] = useState<DailyPnl | null>(null);
  const [monthlyPnl, setMonthlyPnl] = useState<MonthlyPnl | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchPnl = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const [today, monthly] = await Promise.all([
        getTodayPnl(),
        getMonthlyPnl()
      ]);
      setTodayPnl(today);
      setMonthlyPnl(monthly);
    } catch (err: any) {
      console.error('Error fetching P&L:', err);
      setError(err.response?.data?.detail || 'Failed to fetch P&L data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPnl();
  }, [fetchPnl]);

  return {
    todayPnl,
    monthlyPnl,
    loading,
    error,
    refresh: fetchPnl,
  };
};