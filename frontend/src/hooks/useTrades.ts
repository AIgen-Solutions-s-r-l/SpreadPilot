import { useState, useEffect, useCallback } from 'react';
import { getTrades } from '../services/tradeService';
import type { Trade } from '../schemas/trade.schema';
import { useWebSocket } from './useWebSocket';

export const useTrades = (followerId?: string) => {
  const [trades, setTrades] = useState<Trade[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { subscribe } = useWebSocket();

  const fetchTrades = useCallback(async () => {
    try {
      setLoading(true);
      const data = await getTrades(followerId);
      setTrades(data);
      setError(null);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch trades');
    } finally {
      setLoading(false);
    }
  }, [followerId]);

  useEffect(() => {
    fetchTrades();

    // Subscribe to trade updates
    const unsubscribe = subscribe('trade_update', (data: any) => {
      if (!followerId || data.follower_id === followerId) {
        fetchTrades();
      }
    });

    return () => {
      unsubscribe();
    };
  }, [fetchTrades, subscribe, followerId]);

  return { trades, loading, error, refresh: fetchTrades };
};
