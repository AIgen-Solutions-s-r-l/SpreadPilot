import apiClient from './api';
import { LoginCredentials, User } from '../types/auth';

const TOKEN_KEY = 'authToken';

/**
 * Authentication Service
 * Handles all authentication-related API calls and token management
 */

/**
 * Login user with credentials
 * @param credentials - Username and password
 * @returns Promise with access token and token type
 */
export const login = async (credentials: LoginCredentials): Promise<{ access_token: string; token_type: string }> => {
  try {
    // OAuth2 requires form-urlencoded format
    const formData = new URLSearchParams();
    formData.append('username', credentials.username);
    formData.append('password', credentials.password);

    const response = await apiClient.post<{ access_token: string; token_type: string }>(
      '/auth/token',
      formData,
      {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
      }
    );

    // Store token in localStorage
    if (response.data.access_token) {
      localStorage.setItem(TOKEN_KEY, response.data.access_token);
    }

    return response.data;
  } catch (error: any) {
    // Log error for debugging
    console.error('Login error:', error.response?.data || error.message);
    throw new Error(error.response?.data?.detail || 'Login failed. Please check your credentials.');
  }
};

/**
 * Get current authenticated user
 * @returns Promise with user data
 */
export const getCurrentUser = async (): Promise<User> => {
  try {
    // For now, extract username from token since backend doesn't have a /me endpoint
    // In the future, this could call GET /auth/me for full user details
    const token = getToken();
    if (!token) {
      throw new Error('No authentication token found');
    }

    // Decode JWT to get username (payload is base64 encoded)
    const payload = JSON.parse(atob(token.split('.')[1]));
    const username = payload.sub;

    if (!username) {
      throw new Error('Invalid token: no username found');
    }

    // Return basic user object
    // In a real app, this would fetch full user details from the backend
    return {
      id: username,
      username: username,
      email: `${username}@example.com`, // Placeholder
      role: 'admin',
    };
  } catch (error: any) {
    console.error('Get current user error:', error.message);
    throw new Error('Failed to get user information');
  }
};

/**
 * Validate stored token by attempting to fetch user data
 * @returns Promise<boolean> - true if token is valid
 */
export const validateToken = async (): Promise<boolean> => {
  try {
    const token = getToken();
    if (!token) {
      return false;
    }

    // Try to get current user - if it succeeds, token is valid
    await getCurrentUser();
    return true;
  } catch (_error) {
    // Token is invalid or expired
    removeToken();
    return false;
  }
};

/**
 * Logout user by clearing token
 */
export const logout = (): void => {
  removeToken();
};

/**
 * Get stored authentication token
 * @returns Token string or null
 */
export const getToken = (): string | null => {
  return localStorage.getItem(TOKEN_KEY);
};

/**
 * Remove stored authentication token
 */
export const removeToken = (): void => {
  localStorage.removeItem(TOKEN_KEY);
};

/**
 * Check if user is authenticated (has a token)
 * Note: This only checks if a token exists, not if it's valid
 * @returns boolean
 */
export const hasToken = (): boolean => {
  return !!getToken();
};
