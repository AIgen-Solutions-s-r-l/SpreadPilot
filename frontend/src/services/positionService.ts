import apiClient from './api';
import { Position, PositionSchema } from '../schemas/position.schema';
import { z } from 'zod';

export const getPositions = async (followerId?: string): Promise<Position[]> => {
  try {
    const params = followerId ? { follower_id: followerId } : {};
    const response = await apiClient.get('/positions', { params });
    return z.array(PositionSchema).parse(response.data);
  } catch (error) {
    console.error('Failed to fetch positions:', error);
    throw error;
  }
};
