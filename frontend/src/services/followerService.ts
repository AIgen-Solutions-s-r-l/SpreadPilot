import apiClient from './api';
import { 
  FollowerSchema, 
  FollowersResponseSchema, 
  CreateFollowerRequest,
  type Follower 
} from '../schemas/follower.schema';
import { ZodError } from 'zod';

// Get all followers
export const getFollowers = async (): Promise<Follower[]> => {
  try {
    const response = await apiClient.get('/followers');
    // Validate response data with Zod
    const validatedData = FollowersResponseSchema.parse(response.data);
    return validatedData;
  } catch (error) {
    console.error('Failed to fetch followers:', error);
    if (error instanceof ZodError) {
      // Zod validation error
      console.error('Validation errors:', error.issues);
    }
    throw error;
  }
};

// Add a new follower
export const addFollower = async (followerData: CreateFollowerRequest): Promise<Follower> => {
  try {
    const response = await apiClient.post('/followers', followerData);
    // Validate response data with Zod
    const validatedData = FollowerSchema.parse(response.data);
    return validatedData;
  } catch (error) {
    console.error('Failed to add follower:', error);
    if (error instanceof ZodError) {
      console.error('Validation errors:', error.issues);
    }
    throw error;
  }
};

// Enable a follower
export const enableFollower = async (followerId: string): Promise<void> => {
  try {
    await apiClient.post(`/followers/${followerId}/toggle`, { enabled: true });
  } catch (error) {
    console.error(`Failed to enable follower ${followerId}:`, error);
    throw error;
  }
};

// Disable a follower
export const disableFollower = async (followerId: string): Promise<void> => {
  try {
    await apiClient.post(`/followers/${followerId}/toggle`, { enabled: false });
  } catch (error) {
    console.error(`Failed to disable follower ${followerId}:`, error);
    throw error;
  }
};

// Manual close position for a specific follower
export const closeFollowerPosition = async (followerId: string, pin: string): Promise<void> => {
  try {
    await apiClient.post('/manual-close', {
      follower_id: followerId,
      pin: pin,
      close_all: true,
      reason: 'Manual close requested from dashboard'
    });
  } catch (error) {
    console.error(`Failed to close position for follower ${followerId}:`, error);
    if (error.response?.status === 403) {
      throw new Error('Invalid PIN');
    }
    throw error;
  }
};

// Close all positions
export const closeAllPositions = async (pin: string): Promise<void> => {
  try {
    // Get all followers first
    const followers = await getFollowers();
    
    // Close positions for each active follower
    const closePromises = followers
      .filter(f => f.enabled)
      .map(f => closeFollowerPosition(f.id, pin));
    
    await Promise.all(closePromises);
  } catch (error) {
    console.error('Failed to close all positions:', error);
    throw error;
  }
};

// Get follower by ID
export const getFollowerById = async (followerId: string): Promise<Follower> => {
  try {
    const response = await apiClient.get(`/followers/${followerId}`);
    const validatedData = FollowerSchema.parse(response.data);
    return validatedData;
  } catch (error) {
    console.error(`Failed to fetch follower ${followerId}:`, error);
    if (error instanceof ZodError) {
      console.error('Validation errors:', error.issues);
    }
    throw error;
  }
};

// Update follower
export const updateFollower = async (followerId: string, data: Partial<CreateFollowerRequest>): Promise<Follower> => {
  try {
    const response = await apiClient.put(`/followers/${followerId}`, data);
    const validatedData = FollowerSchema.parse(response.data);
    return validatedData;
  } catch (error) {
    console.error(`Failed to update follower ${followerId}:`, error);
    if (error instanceof ZodError) {
      console.error('Validation errors:', error.issues);
    }
    throw error;
  }
};

// Delete follower
export const deleteFollower = async (followerId: string): Promise<void> => {
  try {
    await apiClient.delete(`/followers/${followerId}`);
  } catch (error) {
    console.error(`Failed to delete follower ${followerId}:`, error);
    throw error;
  }
};