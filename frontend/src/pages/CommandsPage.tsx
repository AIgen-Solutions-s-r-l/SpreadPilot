import React, { useState } from 'react';
import {
  Container,
  Typography,
  TextField,
  Button,
  Box,
  Paper,
  Grid,
  CircularProgress,
  Alert,
  AlertTitle,
} from '@mui/material';
import { LoadingButton } from '@mui/lab'; // For buttons with loading state
import * as followerService from '../services/followerService';

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
    <Container maxWidth="md" sx={{ py: 3 }}>
      <Typography variant="h4" component="h1" gutterBottom sx={{ fontWeight: 'bold' }}>
        Manual Commands
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          <AlertTitle>Error</AlertTitle>
          {error}
        </Alert>
      )}
      {successMessage && (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccessMessage(null)}>
          <AlertTitle>Success</AlertTitle>
          {successMessage}
        </Alert>
      )}

      <Grid container spacing={3}>
        {/* Close Single Position */}
        <Grid item xs={12}>
          <Paper elevation={2} sx={{ p: 3 }}>
            <Typography variant="h6" component="h2" gutterBottom>
              Close Follower Position
            </Typography>
            <Grid container spacing={2} alignItems="flex-end">
              <Grid item xs={12} sm={5}>
                <TextField
                  fullWidth
                  label="Follower ID"
                  id="followerId"
                  value={followerId}
                  onChange={(e) => setFollowerId(e.target.value)}
                  disabled={isLoadingCloseOne || isLoadingCloseAll}
                  variant="outlined"
                  size="small"
                />
              </Grid>
              <Grid item xs={12} sm={4}>
                <TextField
                  fullWidth
                  type="password"
                  label="PIN (0312)"
                  id="pinCloseOne"
                  value={pin}
                  onChange={(e) => setPin(e.target.value)}
                  disabled={isLoadingCloseOne || isLoadingCloseAll}
                  variant="outlined"
                  size="small"
                />
              </Grid>
              <Grid item xs={12} sm={3}>
                <LoadingButton
                  fullWidth
                  variant="contained"
                  color="error"
                  onClick={handleClosePosition}
                  loading={isLoadingCloseOne}
                  disabled={isLoadingCloseAll}
                  sx={{height: '40px'}} // Match TextField small height
                >
                  Close Position
                </LoadingButton>
              </Grid>
            </Grid>
          </Paper>
        </Grid>

        {/* Close All Positions */}
        <Grid item xs={12}>
          <Paper elevation={2} sx={{ p: 3 }}>
            <Typography variant="h6" component="h2" gutterBottom>
              Close All Positions
            </Typography>
            <Grid container spacing={2} alignItems="flex-end">
              <Grid item xs={12} sm={5}>
                {/* Empty for alignment */}
              </Grid>
              <Grid item xs={12} sm={4}>
                <TextField
                  fullWidth
                  type="password"
                  label="PIN (0312)"
                  id="pinCloseAll"
                  value={pin}
                  onChange={(e) => setPin(e.target.value)}
                  disabled={isLoadingCloseOne || isLoadingCloseAll}
                  variant="outlined"
                  size="small"
                />
              </Grid>
              <Grid item xs={12} sm={3}>
                <LoadingButton
                  fullWidth
                  variant="contained"
                  color="error"
                  onClick={handleCloseAll}
                  loading={isLoadingCloseAll}
                  disabled={isLoadingCloseOne}
                  sx={{height: '40px'}} // Match TextField small height
                >
                  Close All
                </LoadingButton>
              </Grid>
            </Grid>
          </Paper>
        </Grid>
      </Grid>
    </Container>
  );
};

export default CommandsPage;