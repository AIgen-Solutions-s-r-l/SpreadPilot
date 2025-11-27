import { useState, useEffect, useCallback } from 'react';
import { getAlerts } from '../services/alertService';
import type { Alert } from '../schemas/alert.schema';
import { useWebSocket } from './useWebSocket';

export const useAlerts = (limit: number = 20) => {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { subscribe } = useWebSocket();

  const fetchAlerts = useCallback(async () => {
    try {
      setLoading(true);
      const data = await getAlerts(limit);
      setAlerts(data);
      setError(null);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch alerts');
    } finally {
      setLoading(false);
    }
  }, [limit]);

  useEffect(() => {
    fetchAlerts();

    // Subscribe to alert updates
    const unsubscribe = subscribe('alert', (newAlert: any) => {
      // Add new alert to the top of the list
      setAlerts(prev => [newAlert, ...prev].slice(0, limit));
    });

    return () => {
      unsubscribe();
    };
  }, [fetchAlerts, subscribe, limit]);

  return { alerts, loading, error, refresh: fetchAlerts };
};
