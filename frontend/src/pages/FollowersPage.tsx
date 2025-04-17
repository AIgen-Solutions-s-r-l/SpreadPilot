import React, { useState, useEffect, useCallback } from 'react';
import { Follower, BotStatus, IbGwStatus, AssignmentState } from '../types/follower';
import * as followerService from '../services/followerService';
import { useWebSocket } from '../contexts/WebSocketContext'; // Import WebSocket hook

// Placeholder for AddFollowerModal - will be created later
// import AddFollowerModal from '../components/followers/AddFollowerModal';

const FollowersPage: React.FC = () => {
  const [followers, setFollowers] = useState<Follower[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false); // For Add Follower modal

  const { lastMessage, isConnected } = useWebSocket(); // Get WebSocket state

  const fetchFollowers = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await followerService.getFollowers();
      setFollowers(data);
    } catch (err) {
      setError('Failed to fetch followers.');
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchFollowers();
  }, [fetchFollowers]);

  // --- WebSocket Update Handling ---
  useEffect(() => {
    if (lastMessage) {
      // TODO: Implement logic based on message content
      // Example: If message indicates a follower update, refresh the list or update specific follower
      console.log('Processing WebSocket message in FollowersPage:', lastMessage);
      if (lastMessage.type === 'follower_update' || lastMessage.type === 'pnl_update') {
         // Could update a single follower state or refetch all for simplicity initially
         fetchFollowers();
      }
      // Add more specific update logic based on message structure from backend
    }
  }, [lastMessage, fetchFollowers]);

  // --- Action Handlers ---
  const handleToggleEnable = async (follower: Follower) => {
    try {
      if (follower.enabled) {
        await followerService.disableFollower(follower.id);
      } else {
        await followerService.enableFollower(follower.id);
      }
      // Refetch or update state based on WebSocket message ideally
      // fetchFollowers(); // Simple refetch for now
    } catch (err) {
      alert(`Failed to ${follower.enabled ? 'disable' : 'enable'} follower ${follower.id}`);
    }
  };

  const handleClosePosition = async (followerId: string) => {
    // TODO: Implement PIN input securely
    const pin = prompt('Enter PIN (0312) to close position:');
    if (pin === '0312') { // Hardcoded PIN - VERY INSECURE - Replace with proper handling
      try {
        await followerService.closeFollowerPosition(followerId, pin);
        alert(`Close position command sent for follower ${followerId}`);
        // State update should ideally come via WebSocket
      } catch (err) {
        alert(`Failed to send close position command for follower ${followerId}`);
      }
    } else if (pin !== null) {
      alert('Incorrect PIN.');
    }
  };

  // --- Rendering ---
  if (isLoading) {
    return <div className="p-6">Loading followers...</div>;
  }

  if (error) {
    return <div className="p-6 text-red-600">{error}</div>;
  }

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-4">
        <h1 className="text-2xl font-semibold text-gray-800">Follower Management</h1>
        <button
          onClick={() => setIsModalOpen(true)}
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
        >
          Add New Follower
        </button>
      </div>

      {/* TODO: Add WebSocket connection status indicator */}
      <p className="mb-4 text-sm text-gray-600">WebSocket Status: {isConnected ? 'Connected' : 'Disconnected'}</p>

      <div className="overflow-x-auto bg-white rounded shadow">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              {/* Define table headers */}
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">ID</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Enabled</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Bot Status</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">IB GW Status</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Assignment</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">P&L Today</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">P&L Month</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">P&L Total</th>
              <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {followers.length === 0 ? (
              <tr>
                <td colSpan={9} className="px-6 py-4 text-center text-gray-500">No followers found.</td>
              </tr>
            ) : (
              followers.map((follower) => (
                <tr key={follower.id}>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{follower.id}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    {/* TODO: Add visual indicator (e.g., colored dot) */}
                    {follower.enabled ? 'Yes' : 'No'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{follower.botStatus}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{follower.ibGwStatus}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{follower.assignmentState}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-500">{follower.pnlToday.toFixed(2)}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-500">{follower.pnlMonth.toFixed(2)}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-500">{follower.pnlTotal.toFixed(2)}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-center text-sm font-medium space-x-2">
                    <button
                      onClick={() => handleToggleEnable(follower)}
                      className={`px-2 py-1 text-xs rounded ${
                        follower.enabled
                          ? 'bg-yellow-500 hover:bg-yellow-600 text-white'
                          : 'bg-green-500 hover:bg-green-600 text-white'
                      }`}
                    >
                      {follower.enabled ? 'Disable' : 'Enable'}
                    </button>
                    <button
                      onClick={() => handleClosePosition(follower.id)}
                      className="px-2 py-1 text-xs rounded bg-red-600 hover:bg-red-700 text-white"
                    >
                      Close Pos
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Placeholder for Modal */}
      {/* {isModalOpen && <AddFollowerModal onClose={() => setIsModalOpen(false)} onAdd={fetchFollowers} />} */}
       {isModalOpen && (
         <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50 flex items-center justify-center">
           <div className="relative p-5 border w-96 shadow-lg rounded-md bg-white">
             <h3 className="text-lg font-medium leading-6 text-gray-900">Add New Follower</h3>
             <div className="mt-2 px-7 py-3">
               <p className="text-sm text-gray-500">Add follower form placeholder.</p>
             </div>
             <div className="items-center px-4 py-3">
               <button
                 onClick={() => setIsModalOpen(false)}
                 className="px-4 py-2 bg-gray-500 text-white text-base font-medium rounded-md w-full shadow-sm hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-gray-300"
               >
                 Close
               </button>
             </div>
           </div>
         </div>
       )}
    </div>
  );
};

export default FollowersPage;