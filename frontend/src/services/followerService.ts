import { Follower } from '../types/follower'; // Import the Follower type

// TODO: Replace with actual API base URL, potentially from env vars
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

// Function to get the auth token (replace with actual implementation if needed)
const getAuthToken = (): string | null => {
  return localStorage.getItem('authToken');
};

// Helper function for making authenticated API requests
const fetchWithAuth = async (url: string, options: RequestInit = {}): Promise<Response> => {
  const token = getAuthToken();
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
    ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
  };

  const response = await fetch(url, { ...options, headers });

  if (!response.ok) {
    // Handle non-2xx responses
    const errorData = await response.json().catch(() => ({ message: 'Failed to parse error response' }));
    console.error('API Error:', response.status, errorData);
    throw new Error(errorData.message || `HTTP error! status: ${response.status}`);
  }
  return response;
};

// --- API Functions ---

export const getFollowers = async (): Promise<Follower[]> => {
  try {
    const response = await fetchWithAuth(`${API_BASE_URL}/followers`);
    const data: Follower[] = await response.json();
    // TODO: Add data validation/transformation if necessary
    return data;
  } catch (error) {
    console.error('Failed to fetch followers:', error);
    throw error; // Re-throw to be handled by the caller
  }
};

export const addFollower = async (newFollowerData: Omit<Follower, 'id' | 'pnlToday' | 'pnlMonth' | 'pnlTotal'> /* Adjust type as needed */): Promise<Follower> => {
    // Placeholder - Adjust payload based on actual API requirements
    try {
        const response = await fetchWithAuth(`${API_BASE_URL}/followers`, {
            method: 'POST',
            body: JSON.stringify(newFollowerData),
        });
        const data: Follower = await response.json();
        return data;
    } catch (error) {
        console.error('Failed to add follower:', error);
        throw error;
    }
};


export const enableFollower = async (followerId: string): Promise<void> => {
  try {
    await fetchWithAuth(`${API_BASE_URL}/followers/${followerId}/enable`, {
      method: 'POST', // Or PUT/PATCH depending on API design
    });
  } catch (error) {
    console.error(`Failed to enable follower ${followerId}:`, error);
    throw error;
  }
};

export const disableFollower = async (followerId: string): Promise<void> => {
  try {
    await fetchWithAuth(`${API_BASE_URL}/followers/${followerId}/disable`, {
      method: 'POST', // Or PUT/PATCH depending on API design
    });
  } catch (error) {
    console.error(`Failed to disable follower ${followerId}:`, error);
    throw error;
  }
};

// Manual Command: ClosePosition
export const closeFollowerPosition = async (followerId: string, pin: string): Promise<void> => {
    try {
        // Assuming PIN is sent in the body, adjust if it's a header or query param
        await fetchWithAuth(`${API_BASE_URL}/followers/${followerId}/close-position`, {
            method: 'POST',
            body: JSON.stringify({ pin }), // Send PIN as required by backend
        });
    } catch (error) {
        console.error(`Failed to close position for follower ${followerId}:`, error);
        throw error;
    }
};

// Manual Command: CloseAll (Assuming this is a general endpoint, not follower-specific)
export const closeAllPositions = async (pin: string): Promise<void> => {
    try {
        // Assuming PIN is sent in the body
        await fetchWithAuth(`${API_BASE_URL}/commands/close-all`, { // Adjust endpoint if needed
            method: 'POST',
            body: JSON.stringify({ pin }),
        });
    } catch (error) {
        console.error('Failed to close all positions:', error);
        throw error;
    }
};

// Add other follower-related API functions as needed (e.g., update, delete)