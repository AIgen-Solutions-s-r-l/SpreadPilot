import React from 'react';
import { Chip, Tooltip } from '@mui/material';
import { alpha, useTheme } from '@mui/material/styles';
import {
  CheckCircleOutline as SafeIcon,
  Warning as RiskIcon,
  Error as CriticalIcon,
} from '@mui/icons-material';
import { getTimeValueStatus } from '../../utils/timeValue';

interface TimeValueBadgeProps {
  timeValue?: number;
  size?: 'small' | 'medium';
}

export const TimeValueBadge: React.FC<TimeValueBadgeProps> = ({ timeValue, size = 'small' }) => {
  const theme = useTheme();

  if (timeValue === undefined || timeValue === null) {
    return null;
  }

  const status = getTimeValueStatus(timeValue) || 'critical';

  const statusConfig = {
    safe: {
      color: theme.palette.success.main,
      bgColor: alpha(theme.palette.success.main, 0.1),
      icon: <SafeIcon fontSize="small" />,
      label: 'Safe',
      tooltip: 'Time value > $1.00 - Position is safe',
    },
    risk: {
      color: theme.palette.warning.main,
      bgColor: alpha(theme.palette.warning.main, 0.1),
      icon: <RiskIcon fontSize="small" />,
      label: 'Risk',
      tooltip: 'Time value between $0.10 and $1.00 - Monitor closely',
    },
    critical: {
      color: theme.palette.error.main,
      bgColor: alpha(theme.palette.error.main, 0.1),
      icon: <CriticalIcon fontSize="small" />,
      label: 'Critical',
      tooltip: 'Time value ≤ $0.10 - Auto-liquidation may trigger',
    },
  };

  const config = statusConfig[status];

  return (
    <Tooltip title={config.tooltip}>
      <Chip
        icon={config.icon}
        label={`TV: $${timeValue.toFixed(2)}`}
        size={size}
        sx={{
          backgroundColor: config.bgColor,
          color: config.color,
          fontWeight: 'medium',
          '& .MuiChip-icon': {
            color: config.color,
          },
        }}
      />
    </Tooltip>
  );
};