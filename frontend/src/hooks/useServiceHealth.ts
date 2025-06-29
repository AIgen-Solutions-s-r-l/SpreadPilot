import { useState, useEffect, useCallback, useRef } from 'react';
import apiClient from '../services/api';

export interface SystemHealth {
  cpu_percent: number;
  memory_percent: number;
  disk_percent: number;
  status: 'healthy' | 'warning';
}

export interface ServiceHealth {
  name: string;
  status: 'healthy' | 'unhealthy' | 'unreachable';
  response_time_ms?: number;
  error?: string;
  critical: boolean;
  last_check: string;
}

export interface HealthResponse {
  overall_status: 'GREEN' | 'YELLOW' | 'RED';
  timestamp: string;
  database: {
    status: 'healthy' | 'unhealthy';
    type: string;
  };
  system: SystemHealth;
  services: ServiceHealth[];
}

interface UseServiceHealthOptions {
  pollInterval?: number; // in milliseconds
  enabled?: boolean;
}

interface UseServiceHealthResult {
  health: HealthResponse | null;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  restartService: (serviceName: string) => Promise<void>;
  isRestarting: boolean;
}

export const useServiceHealth = (options: UseServiceHealthOptions = {}): UseServiceHealthResult => {
  const {
    pollInterval = 30000, // Default 30 seconds
    enabled = true
  } = options;

  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isRestarting, setIsRestarting] = useState(false);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  const fetchHealth = useCallback(async () => {
    try {
      setError(null);
      const response = await apiClient.get<HealthResponse>('/health');
      setHealth(response.data);
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to fetch health status';
      setError(errorMessage);
      console.error('Error fetching health status:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  const restartService = useCallback(async (serviceName: string) => {
    setIsRestarting(true);
    try {
      await apiClient.post(`/service/${serviceName}/restart`);
      // Wait a bit before refreshing to allow service to start
      setTimeout(() => {
        fetchHealth();
      }, 5000);
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to restart service';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setIsRestarting(false);
    }
  }, [fetchHealth]);

  useEffect(() => {
    if (!enabled) {
      return;
    }

    // Initial fetch
    fetchHealth();

    // Set up polling
    intervalRef.current = setInterval(fetchHealth, pollInterval);

    // Cleanup
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [fetchHealth, pollInterval, enabled]);

  return {
    health,
    loading,
    error,
    refresh: fetchHealth,
    restartService,
    isRestarting
  };
};

// Helper function to get health color
export const getHealthColor = (status: 'GREEN' | 'YELLOW' | 'RED' | undefined): string => {
  switch (status) {
    case 'GREEN':
      return '#4caf50'; // success color
    case 'YELLOW':
      return '#ff9800'; // warning color
    case 'RED':
      return '#f44336'; // error color
    default:
      return '#9e9e9e'; // grey for unknown
  }
};

// Helper function to get health icon based on status
export const getHealthIcon = (status: 'GREEN' | 'YELLOW' | 'RED' | undefined): string => {
  switch (status) {
    case 'GREEN':
      return 'CheckCircle';
    case 'YELLOW':
      return 'Warning';
    case 'RED':
      return 'Error';
    default:
      return 'Help';
  }
};