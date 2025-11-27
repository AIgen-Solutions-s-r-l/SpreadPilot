import { useState, useEffect, useCallback } from 'react';
import { getPositions } from '../services/positionService';
import type { Position } from '../schemas/position.schema';
import { useWebSocket } from './useWebSocket';

export const usePositions = (followerId?: string) => {
  const [positions, setPositions] = useState<Position[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { subscribe } = useWebSocket();

  const fetchPositions = useCallback(async () => {
    try {
      setLoading(true);
      const data = await getPositions(followerId);
      setPositions(data);
      setError(null);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch positions');
    } finally {
      setLoading(false);
    }
  }, [followerId]);

  useEffect(() => {
    fetchPositions();

    // Subscribe to position updates
    const unsubscribe = subscribe('position_update', (data: any) => {
      // If the update is for this follower (or we're viewing all), refresh
      if (!followerId || data.follower_id === followerId) {
        fetchPositions();
      }
    });

    return () => {
      unsubscribe();
    };
  }, [fetchPositions, subscribe, followerId]);

  return { positions, loading, error, refresh: fetchPositions };
};
