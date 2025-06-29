import React, { createContext, useState, useContext, ReactNode, useEffect, useCallback, useRef } from 'react';
import { useAuth } from './AuthContext'; // To potentially use auth token for connection
import { WebSocketMessage } from '../types/websocket';

// Define the shape of the context data
interface WebSocketContextType {
  isConnected: boolean;
  lastMessage: WebSocketMessage | null; // Store the last received message
  sendMessage: (message: WebSocketMessage | string) => void; // Function to send messages
}

// Create the context
const WebSocketContext = createContext<WebSocketContextType | undefined>(undefined);

// Define the props for the provider component
interface WebSocketProviderProps {
  children: ReactNode;
  url: string; // URL of the WebSocket server
}

// Create the provider component
export const WebSocketProvider: React.FC<WebSocketProviderProps> = ({ children, url }) => {
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
  const ws = useRef<WebSocket | null>(null);
  const { token } = useAuth(); // Get token if needed for authentication

  const connectWebSocket = useCallback(() => {
    // Close existing connection if any
    if (ws.current && ws.current.readyState !== WebSocket.CLOSED) {
      ws.current.close();
    }

    // TODO: Potentially add token to URL query params or handle auth differently if needed
    // const connectionUrl = token ? `${url}?token=${token}` : url;
    const connectionUrl = url; // Using plain URL for now

    console.log(`Attempting to connect WebSocket to ${connectionUrl}`);
    ws.current = new WebSocket(connectionUrl);

    ws.current.onopen = () => {
      console.log('WebSocket Connected');
      setIsConnected(true);
    };

    ws.current.onclose = (event) => {
      console.log('WebSocket Disconnected:', event.reason, event.code);
      setIsConnected(false);
      // Optional: Implement reconnection logic here (e.g., with exponential backoff)
      // setTimeout(connectWebSocket, 5000); // Simple reconnect attempt after 5s
    };

    ws.current.onerror = (error) => {
      console.error('WebSocket Error:', error);
      // Error doesn't necessarily mean disconnection, onclose will handle that
    };

    ws.current.onmessage = (event) => {
      try {
        const messageData = JSON.parse(event.data);
        console.log('WebSocket Message Received:', messageData);
        setLastMessage(messageData);
        // TODO: Implement more sophisticated message handling/dispatching if needed
      } catch (error) {
        console.error('Failed to parse WebSocket message:', event.data, error);
      }
    };
  }, [url]); // Reconnect if URL changes

  useEffect(() => {
    // Connect when the component mounts or URL/token changes
    connectWebSocket();

    // Cleanup function to close WebSocket connection when component unmounts
    return () => {
      if (ws.current) {
        console.log('Closing WebSocket connection');
        ws.current.close();
      }
    };
  }, [connectWebSocket]); // Dependency array includes the memoized connect function

  const sendMessage = useCallback((message: WebSocketMessage | string) => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      try {
        const messageString = JSON.stringify(message);
        console.log('Sending WebSocket Message:', messageString);
        ws.current.send(messageString);
      } catch (error) {
        console.error('Failed to send WebSocket message:', message, error);
      }
    } else {
      console.error('WebSocket is not connected. Cannot send message.');
    }
  }, []);

  const value = {
    isConnected,
    lastMessage,
    sendMessage,
  };

  return <WebSocketContext.Provider value={value}>{children}</WebSocketContext.Provider>;
};

// Custom hook to use the WebSocketContext
export const useWebSocket = (): WebSocketContextType => {
  const context = useContext(WebSocketContext);
  if (context === undefined) {
    throw new Error('useWebSocket must be used within a WebSocketProvider');
  }
  return context;
};