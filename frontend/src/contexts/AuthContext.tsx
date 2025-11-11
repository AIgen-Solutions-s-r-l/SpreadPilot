import React, { createContext, useState, ReactNode, useEffect } from 'react';
import { User, LoginCredentials } from '../types/auth';
import * as authService from '../services/authService';

// Define the shape of the context data
export interface AuthContextType {
  isAuthenticated: boolean;
  user: User | null;
  token: string | null;
  isLoading: boolean;
  login: (credentials: LoginCredentials) => Promise<void>;
  logout: () => void;
}

// Create the context with a default undefined value initially
export const AuthContext = createContext<AuthContextType | undefined>(undefined);

// Define the props for the provider component
interface AuthProviderProps {
  children: ReactNode;
}

// Create the provider component
export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true); // Start loading initially

  // Check for existing token/session on initial load
  useEffect(() => {
    const initializeAuth = async () => {
      const storedToken = authService.getToken();
      if (storedToken) {
        try {
          // Validate token and fetch user data
          const isValid = await authService.validateToken();
          if (isValid) {
            const userData = await authService.getCurrentUser();
            setToken(storedToken);
            setUser(userData);
            setIsAuthenticated(true);
          }
        } catch (error) {
          console.error('Token validation failed:', error);
          // Clear invalid token
          authService.logout();
        }
      }
      setIsLoading(false);
    };

    initializeAuth();
  }, []);

  const login = async (credentials: LoginCredentials) => {
    setIsLoading(true);
    try {
      // Call authentication service
      const response = await authService.login(credentials);

      // Get user data
      const userData = await authService.getCurrentUser();

      // Update state
      setToken(response.access_token);
      setUser(userData);
      setIsAuthenticated(true);
    } catch (error) {
      console.error('Login failed:', error);
      // Clear any partial state
      setToken(null);
      setUser(null);
      setIsAuthenticated(false);
      throw error; // Re-throw for the component to handle
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    // Clear token from storage
    authService.logout();

    // Clear state
    setToken(null);
    setUser(null);
    setIsAuthenticated(false);
  };

  // Value provided to consuming components
  const value = {
    isAuthenticated,
    user,
    token,
    isLoading,
    login,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};