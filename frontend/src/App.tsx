import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './contexts/AuthContext';
import { WebSocketProvider } from './contexts/WebSocketContext'; // Import WebSocketProvider
import ThemeProvider from './theme/ThemeProvider';
import LoginPage from './pages/LoginPage';
import DashboardLayout from './components/layout/DashboardLayout';
import DashboardPage from './pages/DashboardPage'; // Import DashboardPage
import FollowersPage from './pages/FollowersPage';
import TradingActivityPage from './pages/TradingActivityPage'; // Import TradingActivityPage
import LogsPage from './pages/LogsPage';
import CommandsPage from './pages/CommandsPage'; // Import CommandsPage

// TODO: Move WebSocket URL to environment variables
const WEBSOCKET_URL = import.meta.env.REACT_APP_WS_URL;

function App() {
  const { isAuthenticated, isLoading } = useAuth();

  // Show loading indicator while checking auth status
  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <p>Loading...</p> {/* Replace with a proper spinner/loader component later */}
      </div>
    );
  }

  return (
    <ThemeProvider>
      <Routes>
        <Route
          path="/login"
          element={!isAuthenticated ? <LoginPage /> : <Navigate to="/dashboard" replace />} // Redirect if already logged in
        />
        <Route
          path="/*" // All other routes are protected
          element={
            isAuthenticated ? (
              <WebSocketProvider url={WEBSOCKET_URL}>
                <DashboardLayout>
                {/* Define nested routes within the layout */}
                <Routes>
                  <Route path="/dashboard" element={<DashboardPage />} />
                  <Route path="/followers" element={<FollowersPage />} />
                  <Route path="/trading-activity" element={<TradingActivityPage />} />
                  {/* Add routes for Log Console and Manual Commands later */}
                  <Route path="/logs" element={<LogsPage />} />
                  <Route path="/commands" element={<CommandsPage />} />

                  {/* Default route within the dashboard */}
                  <Route index element={<Navigate to="/dashboard" replace />} />
                  <Route path="/" element={<Navigate to="/dashboard" replace />} />

                  {/* Optional: Catch-all for unknown dashboard routes */}
                  {/* <Route path="*" element={<div>Dashboard Page Not Found</div>} /> */}
                </Routes>
                </DashboardLayout>
              </WebSocketProvider>
            ) : (
              <Navigate to="/login" replace />
            )
          }
        />
        {/* Root path redirect is handled by the nested index route now */}
      </Routes>
    </ThemeProvider>
  );
}

export default App;
