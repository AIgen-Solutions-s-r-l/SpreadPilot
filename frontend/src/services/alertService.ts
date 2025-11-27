import apiClient from './api';
import { Alert, AlertSchema } from '../schemas/alert.schema';
import { z } from 'zod';

export const getAlerts = async (limit: number = 20): Promise<Alert[]> => {
  try {
    const response = await apiClient.get('/alerts', { params: { limit } });
    return z.array(AlertSchema).parse(response.data);
  } catch (error) {
    console.error('Failed to fetch alerts:', error);
    throw error;
  }
};
