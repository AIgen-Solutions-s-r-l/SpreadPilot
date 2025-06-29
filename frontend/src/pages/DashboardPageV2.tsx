import React from 'react';
import { Container, Box, CircularProgress, Alert, Button } from '@mui/material';
import {
  BarChart as BarChartIcon,
  TrendingUp as TrendingUpIcon,
  AttachMoney as AttachMoneyIcon,
  CompareArrows as CompareArrowsIcon,
  People as PeopleIcon,
  Shield as ShieldIcon
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';

// Import our custom MUI components
import StatusBanner from '../components/dashboard/StatusBanner';
import MetricCard from '../components/dashboard/MetricCard';
import PerformanceChart from '../components/dashboard/PerformanceChart';
import ActiveFollowersListV2 from '../components/dashboard/ActiveFollowersListV2';
import TradingActivityTimeline from '../components/dashboard/TradingActivityTimeline';
import RecentAlertsV2 from '../components/dashboard/RecentAlertsV2';
import ServiceHealthWidget from '../components/dashboard/ServiceHealthWidget';

// Hooks
import { useDashboard } from '../hooks/useDashboard';

const DashboardPageV2: React.FC = () => {
  const navigate = useNavigate();
  const { metrics, activeFollowers, recentLogs, pnlHistory: _pnlHistory, loading, error, refresh } = useDashboard();

  const handleViewAllFollowers = () => {
    navigate('/followers');
  };

  const handleViewAllActivity = () => {
    navigate('/trading-activity');
  };

  const handleViewAllAlerts = () => {
    navigate('/logs');
  };

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

  // Format P&L values
  const formatPnlValue = (value: number) => {
    const isNegative = value < 0;
    return `${isNegative ? '-' : '+'}$${Math.abs(value).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  // Format P&L change percentages (mock calculation for now)
  const calculateChange = (current: number, previous: number = 0) => {
    if (previous === 0) return '+0.0%';
    const change = ((current - previous) / Math.abs(previous)) * 100;
    return `${change >= 0 ? '+' : ''}${change.toFixed(1)}%`;
  };

  // Build metrics data
  const metricsData = [
    {
      title: 'TOTAL P&L (30D)',
      value: formatPnlValue(metrics.totalPnl),
      change: `${calculateChange(metrics.totalPnl, metrics.totalPnl * 0.9)} from last period`,
      icon: <AttachMoneyIcon />
    },
    {
      title: "TODAY'S P&L",
      value: formatPnlValue(metrics.todayPnl),
      change: `${activeFollowers.filter(f => f.pnlToday > 0).length} profitable followers`,
      icon: <TrendingUpIcon />
    },
    {
      title: 'MONTHLY P&L',
      value: formatPnlValue(metrics.monthlyPnl),
      change: `${calculateChange(metrics.monthlyPnl, metrics.monthlyPnl * 0.95)} from last month`,
      icon: <BarChartIcon />
    },
    {
      title: 'ACTIVE POSITIONS',
      value: `${metrics.activePositions} ($${metrics.positionsValue.toLocaleString()})`,
      change: `Across ${metrics.activeFollowerCount} followers`,
      icon: <CompareArrowsIcon />
    },
    {
      title: 'FOLLOWER COUNT',
      value: `${metrics.activeFollowerCount} Active / ${metrics.followerCount} Total`,
      change: `${metrics.followerCount - metrics.activeFollowerCount} inactive`,
      icon: <PeopleIcon />
    },
    {
      title: 'TRADE COUNT (TODAY)',
      value: metrics.tradeCountToday.toString(),
      change: `${Math.round(metrics.tradeCountToday / Math.max(metrics.activeFollowerCount, 1))} per follower avg`,
      icon: <ShieldIcon />
    },
  ];

  return (
    <Box sx={{ bgcolor: 'background.default', minHeight: '100%', py: 3 }}>
      <Container maxWidth="xl">
        <StatusBanner onRefresh={refresh} />
        
        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr', lg: '1fr 1fr 1fr' }, gap: 3, mb: 3 }}>
          {metricsData.map((metric) => (
            <Box key={metric.title}>
              <MetricCard
                title={metric.title}
                value={metric.value}
                change={metric.change}
                icon={metric.icon}
              />
            </Box>
          ))}
        </Box>
        
        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', lg: '2fr 1fr' }, gap: 3, mb: 3 }}>
          <Box>
            <PerformanceChart />
          </Box>
          <Box>
            <ActiveFollowersListV2 
              followers={activeFollowers} 
              loading={loading}
              onViewAll={handleViewAllFollowers} 
            />
          </Box>
        </Box>
        
        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', lg: '2fr 1fr' }, gap: 3, mb: 3 }}>
          <Box>
            <TradingActivityTimeline onViewAll={handleViewAllActivity} />
          </Box>
          <Box>
            <RecentAlertsV2 
              logs={recentLogs} 
              loading={loading}
              onViewAll={handleViewAllAlerts} 
            />
          </Box>
        </Box>
        
        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', lg: '1fr' }, gap: 3 }}>
          <Box>
            <ServiceHealthWidget />
          </Box>
        </Box>
      </Container>
    </Box>
  );
};

export default DashboardPageV2;