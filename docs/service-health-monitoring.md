# 🏥 Service Health Monitoring

> 🚀 **Comprehensive health monitoring system** for SpreadPilot services with visual status indicators and restart capabilities

## Overview

The Service Health Monitoring system provides real-time visibility into the health of all SpreadPilot microservices, system resources, and database connectivity. It features a visual dashboard widget with RED/YELLOW/GREEN status indicators and one-click service restart functionality.

## Architecture

### Backend Components

#### Health Endpoints (`admin-api`)
- **GET /api/v1/health** - Comprehensive health status
- **POST /api/v1/service/{name}/restart** - Restart specific service
- **GET /api/v1/services** - List monitored services

#### Health Checks
1. **Service Health**: HTTP health checks to each microservice
2. **Database Health**: MongoDB connectivity check
3. **System Resources**: CPU, memory, and disk usage monitoring
4. **Response Time**: Service response time tracking

### Frontend Components

#### useServiceHealth Hook
```typescript
const { health, loading, error, refresh, restartService, isRestarting } = useServiceHealth({
  pollInterval: 30000,  // Poll every 30 seconds
  enabled: true
});
```

#### ServiceHealthWidget Component
- Visual health status display
- System resource metrics
- Service status list with restart buttons
- Expandable/collapsible interface

## Health Status Logic

### Overall Status Determination

| Status | Condition |
|--------|-----------|
| 🟢 **GREEN** | All services healthy, system resources normal |
| 🟡 **YELLOW** | Non-critical services unhealthy |
| 🔴 **RED** | Critical service unhealthy OR system resources critical |

### Service Categories

#### Critical Services
- **trading-bot**: Core trading engine (downtime affects trading)

#### Non-Critical Services
- **watchdog**: Service monitoring (can self-recover)
- **report-worker**: Report generation (can be delayed)
- **alert-router**: Alert delivery (buffered in Redis)

### System Resource Thresholds

| Resource | Warning | Critical |
|----------|---------|----------|
| CPU | > 80% | > 90% |
| Memory | > 80% | > 90% |
| Disk | > 85% | > 95% |

## Visual Indicators

### Status Dots
- 🟢 **Green**: Healthy/normal operation
- 🟡 **Yellow**: Warning/degraded performance
- 🔴 **Red**: Critical/service down

### Animated States
- **Pulsing Red**: Critical status requiring immediate attention
- **Static Colors**: Stable states

## Service Restart Flow

1. **User Action**: Click restart button on unhealthy service
2. **Confirmation**: Modal dialog with warning for critical services
3. **Authentication**: JWT token validation
4. **Restart Command**: Docker restart command execution
5. **Status Update**: 5-second delay before health refresh

## Implementation Details

### Backend Health Check
```python
async def check_service_health(service_name: str, service_config: Dict) -> Dict:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(service_config["url"])
            if response.status_code == 200:
                return {
                    "name": service_name,
                    "status": "healthy",
                    "response_time_ms": response.elapsed.total_seconds() * 1000,
                    "critical": service_config["critical"]
                }
    except Exception as e:
        return {
            "name": service_name,
            "status": "unreachable",
            "error": str(e),
            "critical": service_config["critical"]
        }
```

### Frontend Polling
```typescript
useEffect(() => {
  if (!enabled) return;
  
  // Initial fetch
  fetchHealth();
  
  // Set up polling
  intervalRef.current = setInterval(fetchHealth, pollInterval);
  
  return () => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
    }
  };
}, [fetchHealth, pollInterval, enabled]);
```

## Configuration

### Service Configuration
Services are configured in `admin-api/app/api/v1/endpoints/health.py`:

```python
SERVICES = {
    "trading-bot": {
        "url": "http://trading-bot:8081/health",
        "critical": True,
        "restart_command": "docker restart trading-bot"
    },
    "watchdog": {
        "url": "http://watchdog:8082/health",
        "critical": False,
        "restart_command": "docker restart watchdog"
    }
    # ... more services
}
```

### Frontend Configuration
- **Poll Interval**: Default 30 seconds (configurable)
- **Request Timeout**: 5 seconds per service
- **Restart Delay**: 5 seconds before refresh

## Security Considerations

1. **Authentication Required**: All health endpoints require JWT authentication
2. **Restart Authorization**: Only authenticated admin users can restart services
3. **Audit Logging**: All restart actions are logged with user information
4. **Network Isolation**: Health checks use internal Docker network

## Monitoring Best Practices

1. **Dashboard Placement**: Health widget should be visible on main dashboard
2. **Alert Integration**: Critical health status should trigger alerts
3. **Historical Tracking**: Consider storing health metrics for trend analysis
4. **Graceful Degradation**: Non-critical service failures shouldn't block operations

## Future Enhancements

1. **Historical Charts**: Time-series graphs of system resources
2. **Custom Thresholds**: Configurable warning/critical levels
3. **Health History**: Store health check results for analysis
4. **Automated Recovery**: Auto-restart policies for services
5. **Metrics Export**: Prometheus/Grafana integration
6. **Mobile Notifications**: Push notifications for critical status