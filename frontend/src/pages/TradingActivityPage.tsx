import React, { useState, SyntheticEvent } from 'react';
import {
  Box,
  Container,
  Typography,
  IconButton,
  Tabs,
  Tab,
  Paper,
  Card,
  CardContent,
  Chip,
  Menu,
  MenuItem,
  ListItemIcon,
  ListItemText,
  useTheme,
  Button,
  CircularProgress
} from '@mui/material';
import Grid2 from '@mui/material/Grid';
import { DataGrid, GridColDef, GridRenderCellParams } from '@mui/x-data-grid';
import {
  Refresh as RefreshIcon,
  Settings as SettingsIcon,
  MoreVert as MoreVertIcon,
  ShowChart as ShowChartIcon,
  PieChart as PieChartIcon,
  Timeline as TimelineIcon,
  NotificationsActive as NotificationsActiveIcon,
  Visibility as VisibilityIcon,
  Edit as EditIcon,
  Close as CloseIcon,
  ErrorOutline as ErrorOutlineIcon,
  CheckCircleOutline as CheckCircleOutlineIcon,
  InfoOutlined as InfoOutlinedIcon,
  WarningAmberOutlined as WarningAmberOutlinedIcon,
} from '@mui/icons-material';
import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Tooltip as RechartsTooltip,
  Legend as RechartsLegend,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  BarChart,
  Bar,
} from 'recharts';
import { usePositions } from '../hooks/usePositions';
import { useTrades } from '../hooks/useTrades';
import { Position } from '../schemas/position.schema';
import { Trade } from '../schemas/trade.schema';

type ActiveTab = 0 | 1 | 2 | 3; // For MUI Tabs, index is used

const TabPanel = (props: { children?: React.ReactNode; index: number; value: number }) => {
  const { children, value, index, ...other } = props;
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`trading-activity-tabpanel-${index}`}
      aria-labelledby={`trading-activity-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ pt: 3 }}>{children}</Box>}
    </div>
  );
};

const ActivePositionsSummary: React.FC<{ positions: Position[] }> = ({ positions }) => {
  const theme = useTheme();

  // Calculate aggregate metrics
  const totalPositions = positions.length;
  const totalValue = positions.reduce((sum, p) => sum + (p.market_value || 0), 0);
  const totalUnrealizedPnl = positions.reduce((sum, p) => sum + (p.unrealized_pnl || 0), 0);
  const pnlPercent = totalValue !== 0 ? (totalUnrealizedPnl / totalValue) * 100 : 0;

  const pnlString = totalUnrealizedPnl >= 0 ? `+$${totalUnrealizedPnl.toFixed(2)}` : `-$${Math.abs(totalUnrealizedPnl).toFixed(2)}`;
  const percentString = `(${pnlPercent >= 0 ? '+' : ''}${pnlPercent.toFixed(1)}%)`;

  return (
  <Card sx={{ mb: 3 }}>
    <CardContent>
      <Typography variant="h6" gutterBottom>
        ACTIVE POSITIONS SUMMARY
      </Typography>
      <Typography variant="body1">
        Total: {totalPositions} positions | Value: ${totalValue.toFixed(2)} | P&L:
        <Typography component="span" sx={{ color: totalUnrealizedPnl >= 0 ? theme.palette.trading.profit : theme.palette.trading.loss, fontWeight: 'medium' }}>
          {' '}{pnlString} {percentString}
        </Typography>
      </Typography>
    </CardContent>
  </Card>
)};

const PositionsTable: React.FC<{ positions: Position[] }> = ({ positions }) => {
  const theme = useTheme();
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);

  const handleMenuOpen = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
  };

  const columns: GridColDef[] = [
    { field: 'follower_id', headerName: 'FOLLOWER', flex: 1.5, minWidth: 150 },
    { field: 'symbol', headerName: 'SYMBOL', flex: 1, minWidth: 100 },
    { field: 'quantity', headerName: 'QTY', type: 'number', flex: 0.5, minWidth: 80 },
    { field: 'avg_cost', headerName: 'ENTRY', flex: 1, minWidth: 100, valueFormatter: (params: any) => `$${params.value?.toFixed(2)}` },
    { field: 'current_price', headerName: 'CURRENT', flex: 1, minWidth: 100, valueFormatter: (params: any) => `$${params.value?.toFixed(2) || '0.00'}` },
    {
      field: 'unrealized_pnl',
      headerName: 'P&L',
      flex: 1,
      minWidth: 120,
      renderCell: (params: GridRenderCellParams<any, number>) => {
        const val = params.value || 0;
        const strVal = val >= 0 ? `+$${val.toFixed(2)}` : `-$${Math.abs(val).toFixed(2)}`;
        return (
          <Typography sx={{ color: val < 0 ? theme.palette.trading.loss : theme.palette.trading.profit, fontWeight: 'medium' }}>
            {strVal}
          </Typography>
        );
      },
    },
    {
      field: 'actions',
      headerName: 'ACTIONS',
      sortable: false,
      filterable: false,
      disableColumnMenu: true,
      flex: 0.5,
      minWidth: 100,
      renderCell: () => (
        <IconButton onClick={(event) => handleMenuOpen(event)}>
          <MoreVertIcon />
        </IconButton>
      ),
    },
  ];

  return (
    <Paper sx={{ height: 400, width: '100%' }}>
      <DataGrid
        rows={positions}
        columns={columns}
        getRowId={(row) => row.id || row._id || Math.random().toString()}
        pageSizeOptions={[5, 10, 25]}
        initialState={{
          pagination: {
            paginationModel: { pageSize: 10, page: 0 },
          },
        }}
        density="compact"
        sx={{
          '& .MuiDataGrid-columnHeaders': {
            backgroundColor: theme.palette.background.paper,
            borderBottom: `1px solid ${theme.palette.divider}`,
          },
          '& .MuiDataGrid-cell': {
            borderBottom: `1px solid ${theme.palette.divider}`,
          },
          '& .MuiDataGrid-footerContainer': {
            borderTop: `1px solid ${theme.palette.divider}`,
          },
        }}
      />
      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={handleMenuClose}
      >
        <MenuItem onClick={handleMenuClose}><ListItemIcon><VisibilityIcon fontSize="small" /></ListItemIcon><ListItemText>View Details</ListItemText></MenuItem>
        <MenuItem onClick={handleMenuClose}><ListItemIcon><EditIcon fontSize="small" /></ListItemIcon><ListItemText>Modify Position</ListItemText></MenuItem>
        <MenuItem onClick={handleMenuClose} sx={{color: 'error.main'}}><ListItemIcon><CloseIcon fontSize="small" color="error" /></ListItemIcon><ListItemText>Close Position</ListItemText></MenuItem>
      </Menu>
    </Paper>
  );
};

const PositionDistributionChart: React.FC<{ positions: Position[] }> = ({ positions }) => {
  const theme = useTheme();

  // Group positions by symbol
  const symbolGroups: {[key: string]: number} = {};
  positions.forEach(p => {
    symbolGroups[p.symbol] = (symbolGroups[p.symbol] || 0) + 1;
  });

  const data = Object.entries(symbolGroups).map(([name, value], index) => ({
    name,
    value,
    fill: [theme.palette.primary.main, theme.palette.secondary.main, theme.palette.info.main, theme.palette.warning.main, theme.palette.success.main][index % 5]
  }));

  // If no data, show placeholder
  if (data.length === 0) {
     return (
        <Card sx={{ height: '100%' }}>
            <CardContent sx={{display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%'}}>
                <Typography color="text.secondary">No active positions</Typography>
            </CardContent>
        </Card>
     );
  }

  return (
    <Card sx={{ height: '100%' }}>
      <CardContent>
        <Typography variant="h6" gutterBottom>POSITION DISTRIBUTION</Typography>
        <Box sx={{ height: 300 }}>
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie data={data} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80} label>
                {data.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.fill} />
                ))}
              </Pie>
              <RechartsTooltip />
              <RechartsLegend />
            </PieChart>
          </ResponsiveContainer>
        </Box>
      </CardContent>
    </Card>
  );
};

const TradeHistoryTable: React.FC<{ trades: Trade[] }> = ({ trades }) => {
  const theme = useTheme();
  const columns: GridColDef[] = [
    {
      field: 'timestamps',
      headerName: 'TIME',
      flex: 1,
      minWidth: 150,
      valueGetter: (params: any) => {
        const ts = params.value?.submitted || params.value?.filled;
        return ts ? new Date(ts).toLocaleString() : 'N/A';
      }
    },
    { field: 'follower_id', headerName: 'FOLLOWER', flex: 1.5, minWidth: 150 },
    {
      field: 'side',
      headerName: 'SIDE',
      flex: 0.7,
      minWidth: 100,
      renderCell: (params) => (
        <Chip
          label={params.value}
          size="small"
          color={['BUY', 'LONG'].includes(String(params.value)) ? 'primary' : 'secondary'}
          sx={{ fontWeight: 'medium', backgroundColor: ['BUY', 'LONG'].includes(String(params.value)) ? theme.palette.trading.buy : theme.palette.trading.sell, color: 'white' }}
        />
      )
    },
    { field: 'symbol', headerName: 'SYMBOL', flex: 1, minWidth: 100 },
    { field: 'qty', headerName: 'QTY', type: 'number', flex: 0.5, minWidth: 80 },
    { field: 'fill_price', headerName: 'PRICE', flex: 1, minWidth: 100, valueFormatter: (params: any) => params.value ? `$${params.value.toFixed(2)}` : '-' },
    {
      field: 'status',
      headerName: 'STATUS',
      flex: 1,
      minWidth: 120,
      renderCell: (params) => (
         <Chip label={params.value} size="small" variant="outlined" />
      )
    },
  ];
  return (
    <Paper sx={{ height: 500, width: '100%' }}>
      <DataGrid
        rows={trades}
        columns={columns}
        getRowId={(row) => row.id || row._id || Math.random().toString()}
        pageSizeOptions={[10, 25, 50]}
        density="compact"
      />
    </Paper>
  );
};

const PerformanceDashboard: React.FC = () => {
  const theme = useTheme();
  const chartData = [
    { name: 'Jan', pnl: 4000, trades: 24 },
    { name: 'Feb', pnl: 3000, trades: 13 },
    { name: 'Mar', pnl: 2000, trades: 98 },
    { name: 'Apr', pnl: 2780, trades: 39 },
    { name: 'May', pnl: 1890, trades: 48 },
    { name: 'Jun', pnl: 2390, trades: 38 },
    { name: 'Jul', pnl: 3490, trades: 43 },
  ];

  return (
  <Paper sx={{p:3}}>
    <Typography variant="h6" gutterBottom>PERFORMANCE METRICS</Typography>
    <Grid2 container spacing={3}>
      <Grid2 size={{xs: 12, md: 6}}>
        <Card>
          <CardContent>
            <Typography variant="subtitle1" gutterBottom>Cumulative P&L</Typography>
            <Box sx={{ height: 250 }}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" />
                  <YAxis />
                  <RechartsTooltip />
                  <Line type="monotone" dataKey="pnl" stroke={theme.palette.primary.main} activeDot={{ r: 8 }} />
                </LineChart>
              </ResponsiveContainer>
            </Box>
          </CardContent>
        </Card>
      </Grid2>
      <Grid2 size={{xs: 12, md: 6}}>
        <Card>
          <CardContent>
            <Typography variant="subtitle1" gutterBottom>Trades per Month</Typography>
             <Box sx={{ height: 250 }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" />
                  <YAxis />
                  <RechartsTooltip />
                  <Bar dataKey="trades" fill={theme.palette.secondary.main} />
                </BarChart>
              </ResponsiveContainer>
            </Box>
          </CardContent>
        </Card>
      </Grid2>
    </Grid2>
    <Box mt={3}>
      <Typography variant="h6" gutterBottom>Key Statistics</Typography>
      <Typography variant="body1">Total Trades: 156 | Win Rate: 68% | Avg Win: $245.67 | Avg Loss: $78.45</Typography>
      <Typography variant="body1">Best Day: May 15 (+$4,567.89) | Worst Day: May 12 (-$1,234.56)</Typography>
    </Box>
  </Paper>
)};

const TradingSignalsTable: React.FC<{ trades: Trade[] }> = ({ trades }) => {
  const theme = useTheme();

  // Filter for pending or submitted trades to treat as "Signals"
  // Or display all for now since we don't have separate signals
  const signals = trades;

  const getStatusChip = (status: string) => {
    let color: "success" | "warning" | "error" | "info" | "default" = "default";
    let icon = <InfoOutlinedIcon />;
    switch(status) {
      case 'FILLED': color = 'success'; icon = <CheckCircleOutlineIcon />; break;
      case 'PENDING':
      case 'SUBMITTED': color = 'warning'; icon = <WarningAmberOutlinedIcon />; break;
      case 'REJECTED':
      case 'FAILED':
      case 'CANCELLED': color = 'error'; icon = <ErrorOutlineIcon />; break;
    }
    return <Chip icon={icon} label={status} color={color} size="small" sx={{fontWeight: 'medium'}}/>;
  }

  const columns: GridColDef[] = [
    {
      field: 'timestamps',
      headerName: 'TIME',
      flex: 1,
      minWidth: 150,
      valueGetter: (params: any) => {
        const ts = params.value?.submitted || params.value?.filled;
        return ts ? new Date(ts).toLocaleString() : 'N/A';
      }
    },
    { field: 'symbol', headerName: 'SYMBOL', flex: 1, minWidth: 100 },
    {
      field: 'side',
      headerName: 'SIGNAL',
      flex: 0.7,
      minWidth: 100,
      renderCell: (params) => (
        <Chip
          label={params.value}
          size="small"
          color={['BUY', 'LONG'].includes(String(params.value)) ? 'primary' : 'secondary'}
          sx={{ fontWeight: 'medium', backgroundColor: ['BUY', 'LONG'].includes(String(params.value)) ? theme.palette.trading.buy : theme.palette.trading.sell, color: 'white' }}
        />
      )
    },
    { field: 'qty', headerName: 'DETAILS', flex: 2, minWidth: 200, valueFormatter: (params: any) => `${params.value} units` },
    {
      field: 'status',
      headerName: 'STATUS',
      flex: 1,
      minWidth: 120,
      renderCell: (params) => getStatusChip(params.value as string)
    },
    {
      field: 'actions',
      headerName: 'ACTIONS',
      sortable: false,
      filterable: false,
      disableColumnMenu: true,
      flex: 0.5,
      minWidth: 100,
      renderCell: () => (
        <Button variant="outlined" size="small" startIcon={<VisibilityIcon />}>View</Button>
      ),
    },
  ];
  return (
    <Paper sx={{ height: 500, width: '100%' }}>
      <DataGrid
        rows={signals}
        columns={columns}
        getRowId={(row) => row.id || row._id || Math.random().toString()}
        pageSizeOptions={[10, 25, 50]}
        density="compact"
      />
    </Paper>
  );
};


const TradingActivityPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<ActiveTab>(0);
  const { positions, loading: positionsLoading, refresh: refreshPositions } = usePositions();
  const { trades, loading: tradesLoading, refresh: refreshTrades } = useTrades();

  const handleChangeTab = (_event: SyntheticEvent, newValue: ActiveTab) => {
    setActiveTab(newValue);
  };

  const handleRefresh = () => {
    refreshPositions();
    refreshTrades();
  };

  return (
    <Container maxWidth="xl" sx={{ py: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h4" component="h1" gutterBottom sx={{fontWeight: 'bold'}}>
          Trading Activity
        </Typography>
        <Box>
          <IconButton aria-label="refresh" onClick={handleRefresh}>
            <RefreshIcon />
          </IconButton>
          <IconButton aria-label="settings">
            <SettingsIcon />
          </IconButton>
        </Box>
      </Box>

      <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
        <Tabs value={activeTab} onChange={handleChangeTab} aria-label="trading activity tabs">
          <Tab label="Positions" icon={<ShowChartIcon />} iconPosition="start" id="trading-activity-tab-0" aria-controls="trading-activity-tabpanel-0" />
          <Tab label="History" icon={<TimelineIcon />} iconPosition="start" id="trading-activity-tab-1" aria-controls="trading-activity-tabpanel-1" />
          <Tab label="Performance" icon={<PieChartIcon />} iconPosition="start" id="trading-activity-tab-2" aria-controls="trading-activity-tabpanel-2" />
          <Tab label="Signals" icon={<NotificationsActiveIcon />} iconPosition="start" id="trading-activity-tab-3" aria-controls="trading-activity-tabpanel-3" />
        </Tabs>
      </Box>

      <TabPanel value={activeTab} index={0}>
        {positionsLoading ? <CircularProgress /> : (
          <>
            <ActivePositionsSummary positions={positions} />
            <Grid2 container spacing={3}>
              <Grid2 size={{xs: 12, lg: 8}}>
                <PositionsTable positions={positions} />
              </Grid2>
              <Grid2 size={{xs: 12, lg: 4}}>
                <PositionDistributionChart positions={positions} />
              </Grid2>
            </Grid2>
          </>
        )}
      </TabPanel>
      <TabPanel value={activeTab} index={1}>
        {tradesLoading ? <CircularProgress /> : <TradeHistoryTable trades={trades} />}
      </TabPanel>
      <TabPanel value={activeTab} index={2}>
        <PerformanceDashboard />
      </TabPanel>
      <TabPanel value={activeTab} index={3}>
        {tradesLoading ? <CircularProgress /> : <TradingSignalsTable trades={trades} />}
      </TabPanel>
    </Container>
  );
};

export default TradingActivityPage;