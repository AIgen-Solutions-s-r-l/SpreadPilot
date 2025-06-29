import React, { useState } from 'react';
import {
  Container,
  Typography,
  Button,
  Box,
  Paper,
  TextField,
  InputAdornment,
  IconButton,
  Menu,
  MenuItem,
  ListItemIcon,
  ListItemText,
  Chip,
  Collapse,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  useTheme,
  alpha,
  Alert,
  CircularProgress,
} from '@mui/material';
import Grid2 from '@mui/material/Grid';
import { DataGrid, GridColDef, GridRenderCellParams, GridActionsCellItem } from '@mui/x-data-grid';
import {
  Add as AddIcon,
  Search as SearchIcon,
  CheckCircleOutline as CheckCircleOutlineIcon,
  HighlightOff as HighlightOffIcon,
  WarningAmberOutlined as WarningAmberOutlinedIcon,
  ErrorOutline as ErrorOutlineIcon,
  MoreVert as MoreVertIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  Close as CloseIcon,
  Refresh as RefreshIcon,
} from '@mui/icons-material';
// import { LineChart, Line, YAxis, ResponsiveContainer } from 'recharts';

// Hooks and services
import { useFollowers } from '../hooks/useFollowers';
import { enableFollower, disableFollower, closeFollowerPosition, addFollower } from '../services/followerService';
import type { Follower, CreateFollowerRequest } from '../schemas/follower.schema';
import { TimeValueBadge } from '../components/common/TimeValueBadge';

// Helper functions for status chips
const getStatusChipProps = (status: string, theme: any) => {
  const statusMap: Record<string, any> = {
    'RUNNING': {
      label: 'RUNNING',
      color: 'success' as const,
      icon: <CheckCircleOutlineIcon />,
      sx: { backgroundColor: alpha(theme.palette.success.main, 0.1), color: 'success.dark', fontWeight:'medium' }
    },
    'CONNECTED': {
      label: 'CONNECTED',
      color: 'success' as const,
      icon: <CheckCircleOutlineIcon />,
      sx: { backgroundColor: alpha(theme.palette.success.main, 0.1), color: 'success.dark', fontWeight:'medium' }
    },
    'STOPPED': {
      label: 'STOPPED',
      color: 'default' as const,
      icon: <HighlightOffIcon />,
      sx: { backgroundColor: alpha(theme.palette.grey[500], 0.1), color: 'text.secondary', fontWeight:'medium' }
    },
    'DISCONNECTED': {
      label: 'DISCONNECTED',
      color: 'default' as const,
      icon: <HighlightOffIcon />,
      sx: { backgroundColor: alpha(theme.palette.grey[500], 0.1), color: 'text.secondary', fontWeight:'medium' }
    },
    'CONNECTING': {
      label: 'CONNECTING',
      color: 'warning' as const,
      icon: <WarningAmberOutlinedIcon />,
      sx: { backgroundColor: alpha(theme.palette.warning.main, 0.1), color: 'warning.dark', fontWeight:'medium' }
    },
    'ERROR': {
      label: 'ERROR',
      color: 'error' as const,
      icon: <ErrorOutlineIcon />,
      sx: { backgroundColor: alpha(theme.palette.error.main, 0.1), color: 'error.dark', fontWeight:'medium' }
    },
  };

  return statusMap[status] || { label: status, color: 'default' as const, sx: {fontWeight:'medium'} };
};

const FollowersPageV2: React.FC = () => {
  const theme = useTheme();
  const { followers, loading, error, todayPnl, monthlyPnl, refresh } = useFollowers();
  
  const [expandedRow, setExpandedRow] = useState<string | null>(null);
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [openAddDialog, setOpenAddDialog] = useState(false);
  const [openConfirmDialog, setOpenConfirmDialog] = useState(false);
  const [actionFollower, setActionFollower] = useState<Follower | null>(null);
  const [actionType, setActionType] = useState<string | null>(null);
  const [pin, setPin] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  
  // Add follower form state
  const [newFollower, setNewFollower] = useState<Partial<CreateFollowerRequest>>({
    name: '',
    email: '',
    iban: '',
    commission_pct: 0,
  });

  const [anchorEl, setAnchorEl] = React.useState<null | HTMLElement>(null);
  const openActionMenu = Boolean(anchorEl);

  const handleActionMenuClick = (event: React.MouseEvent<HTMLElement>, follower: Follower) => {
    setAnchorEl(event.currentTarget);
    setActionFollower(follower);
  };
  
  const handleActionMenuClose = () => {
    setAnchorEl(null);
    setActionFollower(null);
  };

  const handleRowClick = (id: string) => {
    setExpandedRow(expandedRow === id ? null : id);
  };

  const handleOpenAddDialog = () => {
    setNewFollower({
      name: '',
      email: '',
      iban: '',
      commission_pct: 0,
    });
    setOpenAddDialog(true);
  };
  
  const handleCloseAddDialog = () => {
    setOpenAddDialog(false);
    setNewFollower({
      name: '',
      email: '',
      iban: '',
      commission_pct: 0,
    });
  };
  
  const handleAddFollower = async () => {
    try {
      if (!newFollower.name || !newFollower.email || !newFollower.iban) {
        alert('Please fill in all required fields');
        return;
      }
      
      await addFollower(newFollower as CreateFollowerRequest);
      await refresh();
      handleCloseAddDialog();
    } catch (error: any) {
      alert(error.message || 'Failed to add follower');
    }
  };

  const handleConfirmAction = (follower: Follower, type: string) => {
    setActionFollower(follower);
    setActionType(type);
    setOpenConfirmDialog(true);
    handleActionMenuClose();
  };
  
  const handleCloseConfirmDialog = () => {
    setOpenConfirmDialog(false);
    setActionFollower(null);
    setActionType(null);
    setPin('');
  };
  
  const executeConfirmedAction = async () => {
    if (!actionFollower || !actionType) return;
    
    try {
      switch (actionType) {
        case 'ENABLE':
          await enableFollower(actionFollower.id);
          break;
        case 'DISABLE':
          await disableFollower(actionFollower.id);
          break;
        case 'CLOSE_POSITIONS':
          if (!pin) {
            alert('PIN is required');
            return;
          }
          await closeFollowerPosition(actionFollower.id, pin);
          break;
      }
      
      // Refresh data after action
      await refresh();
      handleCloseConfirmDialog();
    } catch (error: any) {
      alert(error.message || 'Action failed');
    }
  };

  // Filter followers based on search
  const filteredFollowers = followers.filter(f => 
    f.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
    f.name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    f.email?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const columns: GridColDef<Follower>[] = [
    {
      field: 'id',
      headerName: 'ID',
      flex: 1,
      minWidth: 150,
      renderCell: (params: GridRenderCellParams) => (
        <Box sx={{ display: 'flex', alignItems: 'center' }}>
          <IconButton size="small" onClick={() => handleRowClick(params.row.id)} sx={{ mr: 1 }}>
            {expandedRow === params.row.id ? <ExpandLessIcon /> : <ExpandMoreIcon />}
          </IconButton>
          <Typography variant="body2" fontWeight="medium">{params.row.id}</Typography>
        </Box>
      )
    },
    {
      field: 'enabled',
      headerName: 'Status',
      flex: 1,
      minWidth: 120,
      renderCell: (params: GridRenderCellParams) => {
        const chipProps = params.value 
          ? getStatusChipProps('RUNNING', theme)
          : getStatusChipProps('STOPPED', theme);
        return <Chip {...chipProps} size="small" />;
      },
    },
    {
      field: 'botStatus',
      headerName: 'Bot',
      flex: 1,
      minWidth: 100,
      renderCell: (params: GridRenderCellParams) => {
        if (!params.value) return null;
        const chipProps = getStatusChipProps(params.value, theme);
        return <Chip {...chipProps} size="small" />;
      },
    },
    {
      field: 'ibGwStatus',
      headerName: 'IB GW',
      flex: 1,
      minWidth: 120,
      renderCell: (params: GridRenderCellParams) => {
        if (!params.value) return null;
        const chipProps = getStatusChipProps(params.value, theme);
        return <Chip {...chipProps} size="small" />;
      },
    },
    {
      field: 'timeValue',
      headerName: 'TV',
      flex: 1,
      minWidth: 100,
      renderCell: (params: GridRenderCellParams) => (
        <TimeValueBadge timeValue={params.value} />
      ),
    },
    {
      field: 'pnlToday',
      headerName: 'P&L Today',
      flex: 1,
      minWidth: 120,
      renderCell: (params: GridRenderCellParams) => {
        const value = params.value || 0;
        const isNegative = value < 0;
        return (
          <Typography 
            variant="body2" 
            sx={{ 
              color: isNegative ? theme.palette.error.main : theme.palette.success.main,
              fontWeight: 'medium' 
            }}
          >
            {isNegative ? '-' : '+'}${Math.abs(value).toFixed(2)}
          </Typography>
        );
      },
    },
    {
      field: 'pnlMonth',
      headerName: 'P&L Month',
      flex: 1,
      minWidth: 120,
      renderCell: (params: GridRenderCellParams) => {
        const value = params.value || 0;
        const isNegative = value < 0;
        return (
          <Typography 
            variant="body2" 
            sx={{ 
              color: isNegative ? theme.palette.error.main : theme.palette.success.main,
              fontWeight: 'medium' 
            }}
          >
            {isNegative ? '-' : '+'}${Math.abs(value).toFixed(2)}
          </Typography>
        );
      },
    },
    {
      field: 'actions',
      type: 'actions',
      headerName: 'Actions',
      flex: 0.5,
      minWidth: 80,
      getActions: (params) => [
        <GridActionsCellItem
          icon={<MoreVertIcon />}
          label="Actions"
          onClick={(e) => handleActionMenuClick(e as any, params.row)}
          showInMenu={false}
        />,
      ],
    },
  ];

  if (loading) {
    return (
      <Container>
        <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
          <CircularProgress />
        </Box>
      </Container>
    );
  }

  if (error) {
    return (
      <Container>
        <Alert severity="error" sx={{ mt: 2 }}>
          {error}
          <Button onClick={refresh} sx={{ ml: 2 }}>Retry</Button>
        </Alert>
      </Container>
    );
  }

  return (
    <Container maxWidth="xl">
      <Box mb={4}>
        <Typography variant="h4" fontWeight="bold" gutterBottom>
          Followers Management
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Manage and monitor your trading followers
        </Typography>
      </Box>

      {/* Summary Stats */}
      <Grid2 container spacing={3} mb={3}>
        <Grid2 size={{ xs: 12, sm: 6, md: 3 }}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="subtitle2" color="text.secondary" gutterBottom>
              Total Followers
            </Typography>
            <Typography variant="h4">{followers.length}</Typography>
          </Paper>
        </Grid2>
        <Grid2 size={{ xs: 12, sm: 6, md: 3 }}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="subtitle2" color="text.secondary" gutterBottom>
              Active Followers
            </Typography>
            <Typography variant="h4">{followers.filter(f => f.enabled).length}</Typography>
          </Paper>
        </Grid2>
        <Grid2 size={{ xs: 12, sm: 6, md: 3 }}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="subtitle2" color="text.secondary" gutterBottom>
              Today's P&L
            </Typography>
            <Typography 
              variant="h4" 
              sx={{ 
                color: todayPnl && todayPnl.total_pnl < 0 
                  ? theme.palette.error.main 
                  : theme.palette.success.main 
              }}
            >
              ${todayPnl?.total_pnl.toFixed(2) || '0.00'}
            </Typography>
          </Paper>
        </Grid2>
        <Grid2 size={{ xs: 12, sm: 6, md: 3 }}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="subtitle2" color="text.secondary" gutterBottom>
              Month's P&L
            </Typography>
            <Typography 
              variant="h4" 
              sx={{ 
                color: monthlyPnl && monthlyPnl.total_pnl < 0 
                  ? theme.palette.error.main 
                  : theme.palette.success.main 
              }}
            >
              ${monthlyPnl?.total_pnl.toFixed(2) || '0.00'}
            </Typography>
          </Paper>
        </Grid2>
      </Grid2>

      {/* Actions Bar */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Box display="flex" justifyContent="space-between" alignItems="center" flexWrap="wrap" gap={2}>
          <Box display="flex" gap={2} alignItems="center">
            <TextField
              placeholder="Search followers..."
              size="small"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <SearchIcon />
                  </InputAdornment>
                ),
              }}
            />
            <Button 
              startIcon={<RefreshIcon />} 
              onClick={refresh}
              variant="outlined"
            >
              Refresh
            </Button>
          </Box>
          <Button 
            variant="contained" 
            startIcon={<AddIcon />}
            onClick={handleOpenAddDialog}
          >
            Add Follower
          </Button>
        </Box>
      </Paper>

      {/* Data Grid */}
      <Paper>
        <DataGrid
          rows={filteredFollowers}
          columns={columns}
          initialState={{
            pagination: {
              paginationModel: {
                pageSize: rowsPerPage,
                page: page,
              },
            },
          }}
          pageSizeOptions={[5, 10, 25]}
          onPaginationModelChange={(model) => {
            setRowsPerPage(model.pageSize);
            setPage(model.page);
          }}
          autoHeight
          disableRowSelectionOnClick
          sx={{
            '& .MuiDataGrid-row': {
              cursor: 'pointer'
            }
          }}
        />
        
        {/* Expanded Row Details */}
        {filteredFollowers.map((follower) => (
          <Collapse key={follower.id} in={expandedRow === follower.id}>
            <ExpandedFollowerDetail follower={follower} />
          </Collapse>
        ))}
      </Paper>

      {/* Action Menu */}
      <Menu
        anchorEl={anchorEl}
        open={openActionMenu}
        onClose={handleActionMenuClose}
      >
        <MenuItem onClick={() => handleConfirmAction(actionFollower!, 'ENABLE')}>
          <ListItemIcon><CheckCircleOutlineIcon color="success" /></ListItemIcon>
          <ListItemText>Enable Follower</ListItemText>
        </MenuItem>
        <MenuItem onClick={() => handleConfirmAction(actionFollower!, 'DISABLE')}>
          <ListItemIcon><HighlightOffIcon color="error" /></ListItemIcon>
          <ListItemText>Disable Follower</ListItemText>
        </MenuItem>
        <MenuItem onClick={() => handleConfirmAction(actionFollower!, 'CLOSE_POSITIONS')}>
          <ListItemIcon><CloseIcon color="warning" /></ListItemIcon>
          <ListItemText>Close Positions</ListItemText>
        </MenuItem>
      </Menu>

      {/* Add Dialog */}
      <Dialog open={openAddDialog} onClose={handleCloseAddDialog} maxWidth="sm" fullWidth>
        <DialogTitle>Add New Follower</DialogTitle>
        <DialogContent>
          <TextField 
            margin="dense" 
            label="Name" 
            type="text" 
            fullWidth 
            variant="outlined" 
            value={newFollower.name || ''}
            onChange={(e) => setNewFollower({ ...newFollower, name: e.target.value })}
            required
          />
          <TextField 
            margin="dense" 
            label="Email" 
            type="email" 
            fullWidth 
            variant="outlined" 
            value={newFollower.email || ''}
            onChange={(e) => setNewFollower({ ...newFollower, email: e.target.value })}
            required
          />
          <TextField 
            margin="dense" 
            label="IBAN" 
            type="text" 
            fullWidth 
            variant="outlined" 
            value={newFollower.iban || ''}
            onChange={(e) => setNewFollower({ ...newFollower, iban: e.target.value })}
            required
          />
          <TextField 
            margin="dense" 
            label="Commission %" 
            type="number" 
            fullWidth 
            variant="outlined" 
            value={newFollower.commission_pct || 0}
            onChange={(e) => setNewFollower({ ...newFollower, commission_pct: parseFloat(e.target.value) || 0 })}
            inputProps={{ min: 0, max: 100, step: 0.1 }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseAddDialog}>Cancel</Button>
          <Button onClick={handleAddFollower} variant="contained">Save Follower</Button>
        </DialogActions>
      </Dialog>

      {/* Confirm Dialog */}
      <Dialog open={openConfirmDialog} onClose={handleCloseConfirmDialog}>
        <DialogTitle sx={{display: 'flex', alignItems: 'center'}}>
          <WarningAmberOutlinedIcon color="warning" sx={{mr:1}}/> Confirm Action
        </DialogTitle>
        <DialogContent>
          <Typography>
            Are you sure you want to {actionType?.toLowerCase().replace('_', ' ')} for follower {actionFollower?.id}?
            {actionType === 'CLOSE_POSITIONS' && " This action cannot be undone."}
          </Typography>
          {actionType === 'CLOSE_POSITIONS' && (
            <TextField 
              margin="dense" 
              label="PIN" 
              type="password" 
              fullWidth 
              variant="outlined" 
              sx={{mt:2}}
              value={pin}
              onChange={(e) => setPin(e.target.value)}
            />
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseConfirmDialog}>Cancel</Button>
          <Button 
            onClick={executeConfirmedAction} 
            variant="contained" 
            color={actionType === 'CLOSE_POSITIONS' ? "error" : "primary"}
          >
            Confirm
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
};

export default FollowersPageV2;

// Expanded detail component
const ExpandedFollowerDetail: React.FC<{ follower: Follower }> = ({ follower }) => {
  const theme = useTheme();
  
  return (
    <Box sx={{ p: 2, bgcolor: alpha(theme.palette.primary.light, 0.05), borderTop: `1px solid ${theme.palette.divider}` }}>
      <Grid2 container spacing={2}>
        <Grid2 size={{xs: 12, md: 4}}>
          <Typography variant="subtitle2" gutterBottom color="text.secondary">ACCOUNT DETAILS</Typography>
          <Paper variant="outlined" sx={{p:2}}>
            <Typography variant="body2"><strong>ID:</strong> {follower.id}</Typography>
            <Typography variant="body2"><strong>Name:</strong> {follower.name || 'N/A'}</Typography>
            <Typography variant="body2"><strong>Email:</strong> {follower.email || 'N/A'}</Typography>
            <Typography variant="body2"><strong>IBAN:</strong> {follower.iban || 'N/A'}</Typography>
            <Typography variant="body2"><strong>Commission:</strong> {follower.commission_pct || 0}%</Typography>
          </Paper>
        </Grid2>
        <Grid2 size={{xs: 12, md: 4}}>
          <Typography variant="subtitle2" gutterBottom color="text.secondary">PERFORMANCE</Typography>
          <Paper variant="outlined" sx={{p:2}}>
            <Typography variant="body2">
              <strong>P&L Today:</strong>
              <Typography component="span" sx={{ 
                color: follower.pnlToday < 0 ? theme.palette.error.main : theme.palette.success.main, 
                fontWeight: 'medium' 
              }}> ${follower.pnlToday.toFixed(2)}</Typography>
            </Typography>
            <Typography variant="body2">
              <strong>P&L Month:</strong>
              <Typography component="span" sx={{ 
                color: follower.pnlMonth < 0 ? theme.palette.error.main : theme.palette.success.main, 
                fontWeight: 'medium' 
              }}> ${follower.pnlMonth.toFixed(2)}</Typography>
            </Typography>
            <Typography variant="body2">
              <strong>P&L Total:</strong>
              <Typography component="span" sx={{ 
                color: follower.pnlTotal < 0 ? theme.palette.error.main : theme.palette.success.main, 
                fontWeight: 'medium' 
              }}> ${follower.pnlTotal.toFixed(2)}</Typography>
            </Typography>
          </Paper>
        </Grid2>
        <Grid2 size={{xs: 12, md: 4}}>
          <Typography variant="subtitle2" gutterBottom color="text.secondary">STATUS</Typography>
          <Paper variant="outlined" sx={{p:2}}>
            <Typography variant="body2"><strong>Bot Status:</strong> {follower.botStatus}</Typography>
            <Typography variant="body2"><strong>IB GW Status:</strong> {follower.ibGwStatus}</Typography>
            <Typography variant="body2"><strong>Assignment:</strong> {follower.assignmentState}</Typography>
            <Typography variant="body2">
              <strong>Time Value:</strong> 
              {follower.timeValue ? <TimeValueBadge timeValue={follower.timeValue} size="medium" /> : 'N/A'}
            </Typography>
          </Paper>
        </Grid2>
      </Grid2>
    </Box>
  );
};