import { useState, useEffect, useCallback } from 'react';
import { getFollowers } from '../services/followerService';
import { getTodayPnl, getMonthlyPnl } from '../services/pnlService';
import type { Follower } from '../schemas/follower.schema';
import type { DailyPnl, MonthlyPnl } from '../schemas/pnl.schema';

interface UseFollowersResult {
  followers: Follower[];
  loading: boolean;
  error: string | null;
  todayPnl: DailyPnl | null;
  monthlyPnl: MonthlyPnl | null;
  refresh: () => Promise<void>;
}

export const useFollowers = (autoRefresh: boolean = true, refreshInterval: number = 30000): UseFollowersResult => {
  const [followers, setFollowers] = useState<Follower[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [todayPnl, setTodayPnl] = useState<DailyPnl | null>(null);
  const [monthlyPnl, setMonthlyPnl] = useState<MonthlyPnl | null>(null);

  const fetchData = useCallback(async () => {
    try {
      setError(null);
      
      // Fetch all data in parallel
      const [followersData, todayData, monthData] = await Promise.all([
        getFollowers(),
        getTodayPnl().catch(() => null),
        getMonthlyPnl().catch(() => null),
      ]);

      setFollowers(followersData);
      setTodayPnl(todayData);
      setMonthlyPnl(monthData);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch data');
      console.error('Error fetching followers data:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();

    if (autoRefresh) {
      const interval = setInterval(fetchData, refreshInterval);
      return () => clearInterval(interval);
    }
  }, [fetchData, autoRefresh, refreshInterval]);

  return {
    followers,
    loading,
    error,
    todayPnl,
    monthlyPnl,
    refresh: fetchData,
  };
};

// Hook for individual follower with P&L data
export const useFollowerWithPnl = (followerId: string) => {
  const [follower, setFollower] = useState<Follower | null>(null);
  const [pnlHistory, setPnlHistory] = useState<DailyPnl[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchFollowerData = async () => {
      try {
        setLoading(true);
        setError(null);
        
        // Fetch follower and current month P&L
        const [followersData, monthData] = await Promise.all([
          getFollowers(),
          getMonthlyPnl().catch(() => null),
        ]);

        const followerData = followersData.find(f => f.id === followerId);
        
        if (followerData) {
          setFollower(followerData);
        } else {
          setError('Follower not found');
        }

        if (monthData) {
          setPnlHistory(monthData.daily_breakdown);
        }
      } catch (err: any) {
        setError(err.message || 'Failed to fetch follower data');
        console.error('Error fetching follower data:', err);
      } finally {
        setLoading(false);
      }
    };

    if (followerId) {
      fetchFollowerData();
    }
  }, [followerId]);

  return { follower, pnlHistory, loading, error };
};