import { useState, useEffect, useCallback, useRef } from 'react';
import { getLogs, streamLogs } from '../services/logService';
import type { LogEntry, LogLevel } from '../schemas/log.schema';

interface UseLogsOptions {
  limit?: number;
  level?: LogLevel;
  service?: string;
  search?: string;
  autoRefresh?: boolean;
  refreshInterval?: number;
  streaming?: boolean;
}

interface UseLogsResult {
  logs: LogEntry[];
  totalCount: number;
  loading: boolean;
  error: string | null;
  filters: {
    service: string | null;
    level: string | null;
    search: string | null;
  };
  refresh: () => Promise<void>;
  setFilters: (filters: Partial<UseLogsOptions>) => void;
}

export const useLogs = (options: UseLogsOptions = {}): UseLogsResult => {
  const {
    limit = 200,
    level,
    service,
    search,
    autoRefresh = false,
    refreshInterval = 5000,
    streaming = false,
  } = options;

  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState({
    service: service || null,
    level: level || null,
    search: search || null,
  });
  
  const streamCleanupRef = useRef<(() => void) | null>(null);

  const fetchLogs = useCallback(async () => {
    try {
      setError(null);
      const response = await getLogs(
        limit,
        filters.level as LogLevel | undefined,
        filters.service || undefined,
        filters.search || undefined
      );
      
      setLogs(response.logs);
      setTotalCount(response.count);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch logs');
      console.error('Error fetching logs:', err);
    } finally {
      setLoading(false);
    }
  }, [limit, filters]);

  // Handle streaming logs
  useEffect(() => {
    if (streaming) {
      const cleanup = streamLogs((newLog: LogEntry) => {
        // Apply filters to new log
        if (filters.level && newLog.level !== filters.level) return;
        if (filters.service && newLog.service !== filters.service) return;
        if (filters.search && !newLog.message.toLowerCase().includes(filters.search.toLowerCase())) return;
        
        // Add new log to the beginning and limit the array size
        setLogs(prevLogs => [newLog, ...prevLogs].slice(0, limit));
        setTotalCount(prev => prev + 1);
      });
      
      streamCleanupRef.current = cleanup;
      
      return () => {
        if (streamCleanupRef.current) {
          streamCleanupRef.current();
        }
      };
    }
  }, [streaming, filters, limit]);

  // Initial fetch and auto-refresh
  useEffect(() => {
    fetchLogs();

    if (autoRefresh && !streaming) {
      const interval = setInterval(fetchLogs, refreshInterval);
      return () => clearInterval(interval);
    }
  }, [fetchLogs, autoRefresh, refreshInterval, streaming]);

  const updateFilters = useCallback((newFilters: Partial<UseLogsOptions>) => {
    setFilters(prev => ({
      service: newFilters.service !== undefined ? newFilters.service || null : prev.service,
      level: newFilters.level !== undefined ? newFilters.level || null : prev.level,
      search: newFilters.search !== undefined ? newFilters.search || null : prev.search,
    }));
  }, []);

  return {
    logs,
    totalCount,
    loading,
    error,
    filters,
    refresh: fetchLogs,
    setFilters: updateFilters,
  };
};

// Hook for log statistics
export const useLogStats = () => {
  const [stats, setStats] = useState({
    errorCount: 0,
    warningCount: 0,
    infoCount: 0,
    debugCount: 0,
    criticalCount: 0,
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        // Fetch logs for each level to get counts
        const [critical, errors, warnings, info, debug] = await Promise.all([
          getLogs(1, 'CRITICAL').then(r => r.count).catch(() => 0),
          getLogs(1, 'ERROR').then(r => r.count).catch(() => 0),
          getLogs(1, 'WARNING').then(r => r.count).catch(() => 0),
          getLogs(1, 'INFO').then(r => r.count).catch(() => 0),
          getLogs(1, 'DEBUG').then(r => r.count).catch(() => 0),
        ]);

        setStats({
          criticalCount: critical,
          errorCount: errors,
          warningCount: warnings,
          infoCount: info,
          debugCount: debug,
        });
      } catch (error) {
        console.error('Failed to fetch log stats:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchStats();
  }, []);

  return { stats, loading };
};