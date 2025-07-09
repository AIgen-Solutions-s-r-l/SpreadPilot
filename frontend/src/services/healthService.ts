import apiClient from './api';
import { z } from 'zod';

// Service status enum
export enum ServiceStatus {
  HEALTHY = 'healthy',
  UNHEALTHY = 'unhealthy',
  UNKNOWN = 'unknown'
}

// Service health schema
const ServiceHealthSchema = z.object({
  name: z.string(),
  status: z.enum(['healthy', 'unhealthy', 'unknown']),
  response_time_ms: z.number().optional(),
  critical: z.boolean().optional(),
});

// Overall health schema
const HealthResponseSchema = z.object({
  overall_status: z.enum(['GREEN', 'YELLOW', 'RED']),
  timestamp: z.string(),
  database: z.object({
    status: z.string(),
    type: z.string(),
  }),
  system: z.object({
    cpu_percent: z.number(),
    memory_percent: z.number(),
    disk_percent: z.number(),
    status: z.string(),
  }),
  services: z.array(ServiceHealthSchema),
});

// Time value schema for positions
const TimeValueSchema = z.object({
  follower_id: z.string(),
  time_value: z.number(),
  status: z.enum(['SAFE', 'RISK', 'CRITICAL']),
  positions: z.array(z.object({
    symbol: z.string(),
    expiration: z.string(),
    time_value: z.number(),
  })).optional(),
});

// Type exports
export type ServiceHealth = z.infer<typeof ServiceHealthSchema>;
export type HealthResponse = z.infer<typeof HealthResponseSchema>;
export type TimeValue = z.infer<typeof TimeValueSchema>;

// Get overall health status
export const getHealth = async (): Promise<HealthResponse> => {
  try {
    const response = await apiClient.get('/health');
    const validatedData = HealthResponseSchema.parse(response.data);
    return validatedData;
  } catch (error) {
    console.error('Failed to fetch health status:', error);
    throw error;
  }
};

// Get time value for a specific follower
export const getTimeValue = async (followerId: string): Promise<TimeValue> => {
  try {
    const response = await apiClient.get(`/time-value/${followerId}`);
    const validatedData = TimeValueSchema.parse(response.data);
    return validatedData;
  } catch (error) {
    console.error(`Failed to fetch time value for follower ${followerId}:`, error);
    throw error;
  }
};

// Restart a service
export const restartService = async (serviceName: string): Promise<void> => {
  try {
    await apiClient.post(`/service/${serviceName}/restart`);
  } catch (error) {
    console.error(`Failed to restart service ${serviceName}:`, error);
    throw error;
  }
};

// Get service list
export const getServices = async (): Promise<ServiceHealth[]> => {
  try {
    const response = await apiClient.get('/services');
    const validatedData = z.array(ServiceHealthSchema).parse(response.data);
    return validatedData;
  } catch (error) {
    console.error('Failed to fetch service list:', error);
    throw error;
  }
};

// Utility to determine health color
export const getHealthColor = (status: string): string => {
  switch (status) {
    case 'GREEN':
    case 'healthy':
      return 'green';
    case 'YELLOW':
      return 'yellow';
    case 'RED':
    case 'unhealthy':
      return 'red';
    default:
      return 'gray';
  }
};

// Utility to determine time value badge color
export const getTimeValueBadgeColor = (status: string): string => {
  switch (status) {
    case 'SAFE':
      return 'green';
    case 'RISK':
      return 'yellow';
    case 'CRITICAL':
      return 'red';
    default:
      return 'gray';
  }
};