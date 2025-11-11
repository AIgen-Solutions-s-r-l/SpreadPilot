import React, { createContext, useState, ReactNode, useEffect, useCallback, useRef } from 'react';
import { useAuth } from '../hooks/useAuth'; // To potentially use auth token for connection
import { WebSocketMessage, MessageHandler } from '../types/websocket';

// Define the shape of the context data
interface WebSocketContextType {
  isConnected: boolean;
  lastMessage: WebSocketMessage | null; // Store the last received message
  sendMessage: (message: WebSocketMessage | string) => void; // Function to send messages
  subscribe: (type: string, handler: MessageHandler) => () => void; // Subscribe to specific message types
}

// Create the context
export const WebSocketContext = createContext<WebSocketContextType | undefined>(undefined);

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
  const { token: _token } = useAuth(); // Get token if needed for authentication

  // Subscription system: Map of message type to Set of handlers
  const handlersRef = useRef<Map<string, Set<MessageHandler>>>(new Map());

  const connectWebSocket = useCallback(() => {
    // Close existing connection if any
    if (ws.current && ws.current.readyState !== WebSocket.CLOSED) {
      ws.current.close();
    }

    // Add JWT token to URL query params for authentication
    const connectionUrl = _token ? `${url}?token=${_token}` : url;

    if (import.meta.env.DEV) {
      console.log(`Attempting to connect WebSocket to ${url.split('?')[0]}`); // Log URL without token
    }
    ws.current = new WebSocket(connectionUrl);

    ws.current.onopen = () => {
      if (import.meta.env.DEV) {
        console.log('WebSocket Connected');
      }
      setIsConnected(true);
    };

    ws.current.onclose = (event) => {
      if (import.meta.env.DEV) {
        console.log('WebSocket Disconnected:', event.reason, event.code);
      }
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
        if (import.meta.env.DEV) {
          console.log('WebSocket Message Received:', { type: messageData.type });
        }

        // Keep existing behavior: update lastMessage state
        setLastMessage(messageData);

        // NEW: Dispatch to subscribers
        const handlers = handlersRef.current.get(messageData.type);
        if (handlers && handlers.size > 0) {
          handlers.forEach(handler => {
            try {
              handler(messageData.data);
            } catch (handlerError) {
              console.error(`Error in WebSocket handler for type "${messageData.type}":`, handlerError);
            }
          });
        }
      } catch (error) {
        console.error('Failed to parse WebSocket message:', event.data, error);
      }
    };
  }, [url, _token]); // Reconnect if URL or token changes

  useEffect(() => {
    // Connect when the component mounts or URL/token changes
    connectWebSocket();

    // Cleanup function to close WebSocket connection when component unmounts
    return () => {
      if (ws.current) {
        if (import.meta.env.DEV) {
          console.log('Closing WebSocket connection');
        }
        ws.current.close();
      }
    };
  }, [connectWebSocket]); // Dependency array includes the memoized connect function

  const sendMessage = useCallback((message: WebSocketMessage | string) => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      try {
        const messageString = JSON.stringify(message);
        if (import.meta.env.DEV) {
          console.log('Sending WebSocket Message:', messageString);
        }
        ws.current.send(messageString);
      } catch (error) {
        console.error('Failed to send WebSocket message:', message, error);
      }
    } else {
      console.error('WebSocket is not connected. Cannot send message.');
    }
  }, []);

  const subscribe = useCallback((type: string, handler: MessageHandler) => {
    if (import.meta.env.DEV) {
      console.log(`WebSocket: Subscribing to message type "${type}"`);
    }

    // Get or create handler set for this type
    if (!handlersRef.current.has(type)) {
      handlersRef.current.set(type, new Set());
    }

    handlersRef.current.get(type)!.add(handler);

    // Return unsubscribe function
    return () => {
      if (import.meta.env.DEV) {
        console.log(`WebSocket: Unsubscribing from message type "${type}"`);
      }

      const handlers = handlersRef.current.get(type);
      if (handlers) {
        handlers.delete(handler);

        // Cleanup empty sets to prevent memory leaks
        if (handlers.size === 0) {
          handlersRef.current.delete(type);
        }
      }
    };
  }, []);

  const value = {
    isConnected,
    lastMessage,
    sendMessage,
    subscribe,
  };

  return <WebSocketContext.Provider value={value}>{children}</WebSocketContext.Provider>;
};