import apiClient from './api';
import { Trade, TradeSchema } from '../schemas/trade.schema';
import { z } from 'zod';

export const getTrades = async (followerId?: string): Promise<Trade[]> => {
  try {
    const params = followerId ? { follower_id: followerId } : {};
    const response = await apiClient.get('/trades', { params });
    return z.array(TradeSchema).parse(response.data);
  } catch (error) {
    console.error('Failed to fetch trades:', error);
    throw error;
  }
};
