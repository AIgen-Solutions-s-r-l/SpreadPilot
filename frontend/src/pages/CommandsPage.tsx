import React, { useState } from 'react';
import * as followerService from '../services/followerService'; // Assuming commands are in followerService

const CommandsPage: React.FC = () => {
  const [followerId, setFollowerId] = useState<string>('');
  const [pin, setPin] = useState<string>('');
  const [isLoadingCloseOne, setIsLoadingCloseOne] = useState<boolean>(false);
  const [isLoadingCloseAll, setIsLoadingCloseAll] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const handleClosePosition = async () => {
    if (!followerId || !pin) {
      setError('Follower ID and PIN are required.');
      return;
    }
    // Basic PIN check - Replace with secure handling if possible
    if (pin !== '0312') {
        setError('Incorrect PIN.');
        return;
    }

    setIsLoadingCloseOne(true);
    setError(null);
    setSuccessMessage(null);
    try {
      await followerService.closeFollowerPosition(followerId, pin);
      setSuccessMessage(`Close position command sent successfully for follower ${followerId}.`);
      setFollowerId(''); // Clear fields on success
      setPin('');
    } catch (err: any) {
      setError(err.message || 'Failed to send close position command.');
      console.error(err);
    } finally {
      setIsLoadingCloseOne(false);
    }
  };

  const handleCloseAll = async () => {
     if (!pin) {
      setError('PIN is required.');
      return;
    }
     // Basic PIN check - Replace with secure handling if possible
     if (pin !== '0312') {
        setError('Incorrect PIN.');
        return;
    }

    setIsLoadingCloseAll(true);
    setError(null);
    setSuccessMessage(null);
    try {
      await followerService.closeAllPositions(pin);
      setSuccessMessage('Close all positions command sent successfully.');
       setPin(''); // Clear PIN on success
    } catch (err: any) {
      setError(err.message || 'Failed to send close all positions command.');
      console.error(err);
    } finally {
      setIsLoadingCloseAll(false);
    }
  };

  return (
    <div className="p-6">
      <h1 className="text-2xl font-semibold text-gray-800 mb-6">Manual Commands</h1>

      {error && <div className="mb-4 p-3 text-red-700 bg-red-100 rounded">{error}</div>}
      {successMessage && <div className="mb-4 p-3 text-green-700 bg-green-100 rounded">{successMessage}</div>}

      <div className="space-y-8">
        {/* Close Single Position */}
        <div className="p-4 border rounded shadow-sm bg-white">
          <h2 className="text-lg font-medium text-gray-700 mb-3">Close Follower Position</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-end">
            <div>
              <label htmlFor="followerId" className="block text-sm font-medium text-gray-600 mb-1">Follower ID</label>
              <input
                type="text"
                id="followerId"
                value={followerId}
                onChange={(e) => setFollowerId(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                disabled={isLoadingCloseOne || isLoadingCloseAll}
              />
            </div>
            <div>
              <label htmlFor="pinCloseOne" className="block text-sm font-medium text-gray-600 mb-1">PIN (0312)</label>
              <input
                type="password"
                id="pinCloseOne"
                value={pin} // Use the same PIN state for both for simplicity, or separate if needed
                onChange={(e) => setPin(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                disabled={isLoadingCloseOne || isLoadingCloseAll}
              />
            </div>
            <button
              onClick={handleClosePosition}
              className={`py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white ${
                isLoadingCloseOne
                  ? 'bg-red-400 cursor-not-allowed'
                  : 'bg-red-600 hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500'
              }`}
              disabled={isLoadingCloseOne || isLoadingCloseAll}
            >
              {isLoadingCloseOne ? 'Sending...' : 'Close Position'}
            </button>
          </div>
        </div>

        {/* Close All Positions */}
        <div className="p-4 border rounded shadow-sm bg-white">
          <h2 className="text-lg font-medium text-gray-700 mb-3">Close All Positions</h2>
           <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-end">
             {/* Empty div for alignment */}
             <div></div>
             <div>
               <label htmlFor="pinCloseAll" className="block text-sm font-medium text-gray-600 mb-1">PIN (0312)</label>
               <input
                 type="password"
                 id="pinCloseAll"
                 value={pin} // Use the same PIN state
                 onChange={(e) => setPin(e.target.value)}
                 className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                 disabled={isLoadingCloseOne || isLoadingCloseAll}
               />
             </div>
            <button
              onClick={handleCloseAll}
              className={`py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white ${
                isLoadingCloseAll
                  ? 'bg-red-400 cursor-not-allowed'
                  : 'bg-red-600 hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500'
              }`}
              disabled={isLoadingCloseOne || isLoadingCloseAll}
            >
              {isLoadingCloseAll ? 'Sending...' : 'Close All Positions'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CommandsPage;