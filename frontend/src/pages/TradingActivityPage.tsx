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
  Button
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


// Mock Data Types (keeping existing ones for now, will adapt to MUI DataGrid)
interface Position {
  id: string; // Added for DataGrid
  followerId: string;
  symbol: string;
  qty: number;
  entryPrice: string;
  currentPrice: string;
  pnl: string;
}

interface TradeHistoryItem {
  time: string;
  followerId: string;
  action: 'BUY' | 'SELL';
  symbol: string;
  qty: number;
  price: string;
  pnl?: string; // Optional, only for closing trades
}

interface TradingSignal {
  time: string;
  symbol: string;
  signal: 'BUY' | 'SELL';
  details: string;
  status: 'EXECUTED' | 'PENDING' | 'FAILED' | 'IGNORED';
}

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

const ActivePositionsSummary: React.FC = () => {
  const theme = useTheme();
  return (
  <Card sx={{ mb: 3 }}>
    <CardContent>
      <Typography variant="h6" gutterBottom>
        ACTIVE POSITIONS SUMMARY
      </Typography>
      <Typography variant="body1">
        Total: 24 positions | Value: $245,678.90 | P&L:
        <Typography component="span" sx={{ color: theme.palette.trading.profit, fontWeight: 'medium' }}>
          {' '}+$12,345.67 (+5.3%)
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
    { field: 'followerId', headerName: 'FOLLOWER', flex: 1.5, minWidth: 150 },
    { field: 'symbol', headerName: 'SYMBOL', flex: 1, minWidth: 100 },
    { field: 'qty', headerName: 'QTY', type: 'number', flex: 0.5, minWidth: 80 },
    { field: 'entryPrice', headerName: 'ENTRY', flex: 1, minWidth: 100 },
    { field: 'currentPrice', headerName: 'CURRENT', flex: 1, minWidth: 100 },
    {
      field: 'pnl',
      headerName: 'P&L',
      flex: 1,
      minWidth: 120,
      renderCell: (params: GridRenderCellParams<any, string>) => (
        <Typography sx={{ color: String(params.value).startsWith('-') ? theme.palette.trading.loss : theme.palette.trading.profit, fontWeight: 'medium' }}>
          {String(params.value)}
        </Typography>
      ),
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
        pageSizeOptions={[5, 10, 25]}
        initialState={{
          pagination: {
            paginationModel: { pageSize: 10, page: 0 },
          },
        }}
        density="compact"
        sx={{
          '& .MuiDataGrid-columnHeaders': {
            backgroundColor: theme.palette.background.paper, // Or a light gray
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

const PositionDistributionChart: React.FC = () => {
  const theme = useTheme();
  const data = [
    { name: 'SOXL', value: 55, fill: theme.palette.primary.main },
    { name: 'SOXS', value: 25, fill: theme.palette.secondary.main },
    { name: 'QQQ', value: 20, fill: theme.palette.info.main },
  ];
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

const TradeHistoryTable: React.FC<{ trades: TradeHistoryItem[] }> = ({ trades }) => {
  const theme = useTheme();
  const columns: GridColDef[] = [
    { field: 'time', headerName: 'TIME', flex: 1, minWidth: 150 },
    { field: 'followerId', headerName: 'FOLLOWER', flex: 1.5, minWidth: 150 },
    {
      field: 'action',
      headerName: 'ACTION',
      flex: 0.7,
      minWidth: 100,
      renderCell: (params) => (
        <Chip
          label={params.value}
          size="small"
          color={params.value === 'BUY' ? 'primary' : 'secondary'}
          sx={{ fontWeight: 'medium', backgroundColor: params.value === 'BUY' ? theme.palette.trading.buy : theme.palette.trading.sell, color: 'white' }}
        />
      )
    },
    { field: 'symbol', headerName: 'SYMBOL', flex: 1, minWidth: 100 },
    { field: 'qty', headerName: 'QTY', type: 'number', flex: 0.5, minWidth: 80 },
    { field: 'price', headerName: 'PRICE', flex: 1, minWidth: 100 },
    {
      field: 'pnl',
      headerName: 'P&L',
      flex: 1,
      minWidth: 120,
      renderCell: (params: GridRenderCellParams<any, string | undefined>) => params.value ? (
        <Typography sx={{ color: String(params.value).startsWith('-') ? theme.palette.trading.loss : theme.palette.trading.profit, fontWeight: 'medium' }}>
          {String(params.value)}
        </Typography>
      ) : ('-'),
    },
  ];
  return (
    <Paper sx={{ height: 500, width: '100%' }}>
      <DataGrid rows={trades.map((t, i) => ({...t, id: i}))} columns={columns} pageSizeOptions={[10, 25, 50]} density="compact" />
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

const TradingSignalsTable: React.FC<{ signals: TradingSignal[] }> = ({ signals }) => {
  const theme = useTheme();
  const getStatusChip = (status: TradingSignal['status']) => {
    let color: "success" | "warning" | "error" | "info" | "default" = "default";
    let icon = <InfoOutlinedIcon />;
    switch(status) {
      case 'EXECUTED': color = 'success'; icon = <CheckCircleOutlineIcon />; break;
      case 'PENDING': color = 'warning'; icon = <WarningAmberOutlinedIcon />; break;
      case 'FAILED': color = 'error'; icon = <ErrorOutlineIcon />; break;
      case 'IGNORED': color = 'info'; icon = <InfoOutlinedIcon />; break;
    }
    return <Chip icon={icon} label={status} color={color} size="small" sx={{fontWeight: 'medium'}}/>;
  }

  const columns: GridColDef[] = [
    { field: 'time', headerName: 'TIME', flex: 1, minWidth: 150 },
    { field: 'symbol', headerName: 'SYMBOL', flex: 1, minWidth: 100 },
    {
      field: 'signal',
      headerName: 'SIGNAL',
      flex: 0.7,
      minWidth: 100,
      renderCell: (params) => (
        <Chip
          label={params.value}
          size="small"
          color={params.value === 'BUY' ? 'primary' : 'secondary'}
          sx={{ fontWeight: 'medium', backgroundColor: params.value === 'BUY' ? theme.palette.trading.buy : theme.palette.trading.sell, color: 'white' }}
        />
      )
    },
    { field: 'details', headerName: 'DETAILS', flex: 2, minWidth: 200 },
    {
      field: 'status',
      headerName: 'STATUS',
      flex: 1,
      minWidth: 120,
      renderCell: (params) => getStatusChip(params.value as TradingSignal['status'])
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
      <DataGrid rows={signals.map((s, i) => ({...s, id: i}))} columns={columns} pageSizeOptions={[10, 25, 50]} density="compact" />
    </Paper>
  );
};


const TradingActivityPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<ActiveTab>(0);

  const handleChangeTab = (_event: SyntheticEvent, newValue: ActiveTab) => {
    setActiveTab(newValue);
  };

  // Mock Data
  const mockPositions: Position[] = [
    { id: 'pos1', followerId: 'Follower_001', symbol: 'SOXL', qty: 100, entryPrice: '$45.67', currentPrice: '$47.89', pnl: '+$222.00' },
    { id: 'pos2', followerId: 'Follower_001', symbol: 'QQQ', qty: 25, entryPrice: '$410.25', currentPrice: '$415.75', pnl: '+$137.50' },
    { id: 'pos3', followerId: 'Follower_002', symbol: 'SOXL', qty: 75, entryPrice: '$46.12', currentPrice: '$47.89', pnl: '+$132.75' },
  ];

  const mockTradeHistory: TradeHistoryItem[] = [
    { time: '12:34:56 PM', followerId: 'Follower_001', action: 'BUY', symbol: 'SOXL', qty: 100, price: '$45.67' },
    { time: '12:15:32 PM', followerId: 'Follower_003', action: 'SELL', symbol: 'SOXS', qty: 50, price: '$32.10', pnl: '+$42.50' },
  ];

  const mockTradingSignals: TradingSignal[] = [
    { time: '12:30:00 PM', symbol: 'SOXL', signal: 'BUY', details: '100 shares @ MKT', status: 'EXECUTED' },
    { time: '12:15:00 PM', symbol: 'SOXS', signal: 'SELL', details: '50 shares @ MKT', status: 'EXECUTED' },
    { time: '11:00:00 AM', symbol: 'TQQQ', signal: 'BUY', details: '200 shares @ MKT', status: 'PENDING' },
  ];

  return (
    <Container maxWidth="xl" sx={{ py: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h4" component="h1" gutterBottom sx={{fontWeight: 'bold'}}>
          Trading Activity
        </Typography>
        <Box>
          <IconButton aria-label="refresh">
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
        <ActivePositionsSummary />
        <Grid2 container spacing={3}>
          <Grid2 size={{xs: 12, lg: 8}}>
            <PositionsTable positions={mockPositions} />
          </Grid2>
          <Grid2 size={{xs: 12, lg: 4}}>
            <PositionDistributionChart />
          </Grid2>
        </Grid2>
      </TabPanel>
      <TabPanel value={activeTab} index={1}>
        <TradeHistoryTable trades={mockTradeHistory} />
      </TabPanel>
      <TabPanel value={activeTab} index={2}>
        <PerformanceDashboard />
      </TabPanel>
      <TabPanel value={activeTab} index={3}>
        <TradingSignalsTable signals={mockTradingSignals} />
      </TabPanel>
    </Container>
  );
};

export default TradingActivityPage;