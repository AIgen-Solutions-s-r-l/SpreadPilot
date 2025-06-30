import { useState, useEffect, useCallback } from 'react';
import { getFollowers } from '../services/followerService';
import { getTodayPnl, getMonthlyPnl, calculatePeriodPnl } from '../services/pnlService';
import { getLogs } from '../services/logService';
import { useWebSocket } from './useWebSocket';
import type { Follower } from '../schemas/follower.schema';
// import type { DailyPnl, MonthlyPnl } from '../schemas/pnl.schema';
import type { LogEntry, LogLevel } from '../schemas/log.schema';

interface DashboardMetrics {
  totalPnl: number;
  todayPnl: number;
  monthlyPnl: number;
  activePositions: number;
  positionsValue: number;
  followerCount: number;
  activeFollowerCount: number;
  tradeCountToday: number;
}

interface DashboardData {
  metrics: DashboardMetrics;
  activeFollowers: Follower[];
  recentLogs: LogEntry[];
  pnlHistory: Array<{ date: string; value: number }>;
  loading: boolean;
  error: string | null;
  isConnected: boolean;
  refresh: () => Promise<void>;
}

export const useDashboard = (): DashboardData => {
  const { lastMessage, isConnected } = useWebSocket();
  const [metrics, setMetrics] = useState<DashboardMetrics>({
    totalPnl: 0,
    todayPnl: 0,
    monthlyPnl: 0,
    activePositions: 0,
    positionsValue: 0,
    followerCount: 0,
    activeFollowerCount: 0,
    tradeCountToday: 0,
  });
  const [activeFollowers, setActiveFollowers] = useState<Follower[]>([]);
  const [recentLogs, setRecentLogs] = useState<LogEntry[]>([]);
  const [pnlHistory, setPnlHistory] = useState<Array<{ date: string; value: number }>>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDashboardData = useCallback(async () => {
    try {
      setError(null);
      setLoading(true);

      // Fetch all data in parallel
      const [followers, todayPnl, monthlyPnl, periodPnl, logs] = await Promise.all([
        getFollowers(),
        getTodayPnl(),
        getMonthlyPnl(),
        calculatePeriodPnl(30), // Last 30 days
        getLogs(50, 'ERROR' as LogLevel), // Recent errors
      ]);

      // Calculate metrics
      const activeFollowersList = followers.filter(f => f.enabled);
      const totalPositions = followers.reduce((sum, f) => sum + (f.positions?.count || 0), 0);
      const totalPositionsValue = followers.reduce((sum, f) => sum + (f.positions?.value || 0), 0);
      const tradeCount = todayPnl.trades?.length || 0;

      setMetrics({
        totalPnl: periodPnl.total,
        todayPnl: todayPnl.total_pnl,
        monthlyPnl: monthlyPnl.total_pnl,
        activePositions: totalPositions,
        positionsValue: totalPositionsValue,
        followerCount: followers.length,
        activeFollowerCount: activeFollowersList.length,
        tradeCountToday: tradeCount,
      });

      setActiveFollowers(activeFollowersList);
      setRecentLogs(logs.logs);

      // Create P&L history from monthly data
      if (monthlyPnl.daily_breakdown) {
        const history = monthlyPnl.daily_breakdown
          .slice(-7) // Last 7 days
          .map(day => ({
            date: new Date(day.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
            value: day.total_pnl,
          }));
        setPnlHistory(history);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to fetch dashboard data');
      console.error('Error fetching dashboard data:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  // Handle WebSocket messages for real-time updates
  useEffect(() => {
    if (lastMessage) {
      try {
        const { type, data } = lastMessage as { type: string; data: any };
        
        switch (type) {
          case 'pnl_update':
            // Update P&L metrics in real-time
            setMetrics(prev => ({
              ...prev,
              todayPnl: data.todayPnl || prev.todayPnl,
              totalPnl: data.totalPnl || prev.totalPnl,
              monthlyPnl: data.monthlyPnl || prev.monthlyPnl,
            }));
            break;
            
          case 'position_update':
            // Update position counts
            setMetrics(prev => ({
              ...prev,
              activePositions: data.activePositions || prev.activePositions,
              positionsValue: data.positionsValue || prev.positionsValue,
            }));
            break;
            
          case 'trade_update':
            // Update trade count
            setMetrics(prev => ({
              ...prev,
              tradeCountToday: data.tradeCountToday || prev.tradeCountToday,
            }));
            break;
            
          case 'follower_update':
            // Update follower data
            if (data.followers) {
              setActiveFollowers(data.followers.filter((f: Follower) => f.enabled));
              setMetrics(prev => ({
                ...prev,
                followerCount: data.followers.length,
                activeFollowerCount: data.followers.filter((f: Follower) => f.enabled).length,
              }));
            }
            break;
            
          case 'log_update':
            // Add new log entries
            if (data.log) {
              setRecentLogs(prev => [data.log, ...prev.slice(0, 49)]); // Keep last 50 logs
            }
            break;
            
          default:
            console.log('Unknown WebSocket message type:', type);
        }
      } catch (error) {
        console.error('Error processing WebSocket message:', error);
      }
    }
  }, [lastMessage]);

  useEffect(() => {
    fetchDashboardData();
    
    // Auto-refresh every 30 seconds (reduced since we have WebSocket updates)
    const interval = setInterval(fetchDashboardData, 30000);
    return () => clearInterval(interval);
  }, [fetchDashboardData]);

  return {
    metrics,
    activeFollowers,
    recentLogs,
    pnlHistory,
    loading,
    error,
    isConnected,
    refresh: fetchDashboardData,
  };
};

// Hook for real-time metrics updates via WebSocket
export const useRealtimeMetrics = () => {
  const [realtimeData, _setRealtimeData] = useState({
    lastUpdate: new Date(),
    pnlChange: 0,
    newTrades: 0,
    alerts: 0,
  });

  useEffect(() => {
    // TODO: Subscribe to WebSocket events for real-time updates
    // This would integrate with the WebSocketContext
  }, []);

  return realtimeData;
};