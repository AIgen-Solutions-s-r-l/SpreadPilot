import React, { createContext, useState, useContext, ReactNode, useEffect } from 'react';
// Placeholder for API service - will be created later
// import * as authService from '../services/authService';

// Define the shape of the context data
interface AuthContextType {
  isAuthenticated: boolean;
  user: any; // Replace 'any' with a proper User type/interface later
  token: string | null;
  isLoading: boolean;
  login: (/* credentials */) => Promise<void>; // Define credentials type later
  logout: () => void;
}

// Create the context with a default undefined value initially
const AuthContext = createContext<AuthContextType | undefined>(undefined);

// Define the props for the provider component
interface AuthProviderProps {
  children: ReactNode;
}

// Create the provider component
export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [user, setUser] = useState<any>(null); // Replace 'any'
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true); // Start loading initially

  // TODO: Check for existing token/session on initial load (e.g., from localStorage)
  useEffect(() => {
    // Simulate checking local storage or session
    const storedToken = localStorage.getItem('authToken');
    if (storedToken) {
      // TODO: Validate token with backend, fetch user data
      setToken(storedToken);
      setIsAuthenticated(true);
      // setUser(fetchedUserData); // Fetch user data based on token
    }
    setIsLoading(false); // Finished initial check
  }, []);

  const login = async (/* credentials */) => {
    setIsLoading(true);
    try {
      // TODO: Call actual authService.login(credentials)
      // const { token: newToken, user: loggedInUser } = await authService.login(credentials);
      throw new Error('Authentication service not implemented');
    } catch (error) {
      console.error('Login failed:', error);
      // Handle login error (e.g., show message to user)
      throw error; // Re-throw for the component to handle
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    localStorage.removeItem('authToken');
    setToken(null);
    setUser(null);
    setIsAuthenticated(false);
    // Optionally redirect to login page
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

// Custom hook to use the AuthContext
export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};