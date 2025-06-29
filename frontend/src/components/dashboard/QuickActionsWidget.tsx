import React, { useState } from 'react';
import {
  Card,
  CardContent,
  Typography,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Box,
  Alert,
  Stack,
} from '@mui/material';
import { LoadingButton } from '@mui/lab';
import { Emergency, Stop, Settings } from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { closeAllPositions } from '../../services/followerService';

const QuickActionsWidget: React.FC = () => {
  const navigate = useNavigate();
  const [emergencyDialogOpen, setEmergencyDialogOpen] = useState(false);
  const [pin, setPin] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const handleEmergencyStop = async () => {
    if (!pin) {
      setError('PIN is required');
      return;
    }

    setIsLoading(true);
    setError(null);
    setSuccess(null);

    try {
      await closeAllPositions(pin);
      setSuccess('Emergency stop initiated. All positions are being closed.');
      setPin('');
      setEmergencyDialogOpen(false);
    } catch (err: any) {
      setError(err.message || 'Failed to initiate emergency stop');
    } finally {
      setIsLoading(false);
    }
  };

  const closeDialog = () => {
    setEmergencyDialogOpen(false);
    setPin('');
    setError(null);
    setSuccess(null);
  };

  return (
    <>
      <Card sx={{ height: '100%' }}>
        <CardContent>
          <Typography variant="h6" component="h2" gutterBottom>
            Quick Actions
          </Typography>
          
          <Stack spacing={2}>
            <Button
              variant="outlined"
              color="error"
              startIcon={<Emergency />}
              onClick={() => setEmergencyDialogOpen(true)}
              fullWidth
            >
              Emergency Stop
            </Button>
            
            <Button
              variant="outlined"
              color="warning"
              startIcon={<Stop />}
              onClick={() => navigate('/commands')}
              fullWidth
            >
              Manual Commands
            </Button>
            
            <Button
              variant="outlined"
              startIcon={<Settings />}
              onClick={() => navigate('/followers')}
              fullWidth
            >
              Manage Followers
            </Button>
          </Stack>

          {success && (
            <Alert severity="success" sx={{ mt: 2 }}>
              {success}
            </Alert>
          )}
        </CardContent>
      </Card>

      <Dialog open={emergencyDialogOpen} onClose={closeDialog} maxWidth="sm" fullWidth>
        <DialogTitle>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Emergency color="error" />
            Emergency Stop - Close All Positions
          </Box>
        </DialogTitle>
        <DialogContent>
          <Alert severity="warning" sx={{ mb: 2 }}>
            This will immediately close ALL positions for ALL followers. This action cannot be undone.
          </Alert>
          
          <TextField
            autoFocus
            margin="dense"
            label="Enter PIN (0312)"
            type="password"
            fullWidth
            variant="outlined"
            value={pin}
            onChange={(e) => setPin(e.target.value)}
            error={!!error}
            helperText={error}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={closeDialog} disabled={isLoading}>
            Cancel
          </Button>
          <LoadingButton
            onClick={handleEmergencyStop}
            loading={isLoading}
            variant="contained"
            color="error"
          >
            Confirm Emergency Stop
          </LoadingButton>
        </DialogActions>
      </Dialog>
    </>
  );
};

export default QuickActionsWidget;