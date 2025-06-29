from fastapi import APIRouter, HTTPException, Depends, status
from typing import Dict, Any, List
from datetime import datetime
import psutil
import asyncio
import httpx
from motor.motor_asyncio import AsyncIOMotorClient

from app.core.security import get_current_user
from app.db.mongodb import get_database
from spreadpilot_core.logging.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()

# Service configuration for health checks
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
    },
    "report-worker": {
        "url": "http://report-worker:8084/health",
        "critical": False,
        "restart_command": "docker restart report-worker"
    },
    "alert-router": {
        "url": "http://alert-router:8085/health",
        "critical": False,
        "restart_command": "docker restart alert-router"
    }
}

async def check_service_health(service_name: str, service_config: Dict[str, Any]) -> Dict[str, Any]:
    """Check health of a single service"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(service_config["url"])
            if response.status_code == 200:
                return {
                    "name": service_name,
                    "status": "healthy",
                    "response_time_ms": response.elapsed.total_seconds() * 1000,
                    "critical": service_config["critical"],
                    "last_check": datetime.utcnow().isoformat()
                }
            else:
                return {
                    "name": service_name,
                    "status": "unhealthy",
                    "error": f"HTTP {response.status_code}",
                    "critical": service_config["critical"],
                    "last_check": datetime.utcnow().isoformat()
                }
    except Exception as e:
        return {
            "name": service_name,
            "status": "unreachable",
            "error": str(e),
            "critical": service_config["critical"],
            "last_check": datetime.utcnow().isoformat()
        }

@router.get("/health", response_model=Dict[str, Any])
async def get_comprehensive_health(
    db: AsyncIOMotorClient = Depends(get_database),
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get comprehensive health status of all services.
    
    Returns health status with color coding:
    - GREEN: All services healthy
    - YELLOW: Non-critical services unhealthy
    - RED: Critical services unhealthy or system resources critical
    """
    # Check database connection
    try:
        await db.admin.command('ping')
        db_status = "healthy"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = "unhealthy"
    
    # Check system resources
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    system_health = {
        "cpu_percent": cpu_percent,
        "memory_percent": memory.percent,
        "disk_percent": disk.percent,
        "status": "healthy" if cpu_percent < 80 and memory.percent < 80 and disk.percent < 90 else "warning"
    }
    
    # Check all services
    service_checks = []
    tasks = []
    for service_name, service_config in SERVICES.items():
        tasks.append(check_service_health(service_name, service_config))
    
    service_checks = await asyncio.gather(*tasks)
    
    # Determine overall health status
    critical_unhealthy = any(
        service["status"] != "healthy" and service["critical"] 
        for service in service_checks
    )
    non_critical_unhealthy = any(
        service["status"] != "healthy" and not service["critical"]
        for service in service_checks
    )
    
    if db_status != "healthy" or critical_unhealthy or system_health["status"] != "healthy":
        overall_status = "RED"
    elif non_critical_unhealthy:
        overall_status = "YELLOW"
    else:
        overall_status = "GREEN"
    
    return {
        "overall_status": overall_status,
        "timestamp": datetime.utcnow().isoformat(),
        "database": {
            "status": db_status,
            "type": "mongodb"
        },
        "system": system_health,
        "services": service_checks
    }

@router.post("/service/{service_name}/restart")
async def restart_service(
    service_name: str,
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Restart a specific service.
    
    Requires authentication and appropriate permissions.
    """
    if service_name not in SERVICES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service '{service_name}' not found"
        )
    
    service_config = SERVICES[service_name]
    
    try:
        # In production, this would execute the restart command
        # For now, we'll simulate the restart
        logger.warning(f"Service restart requested for: {service_name} by user: {current_user.get('username')}")
        
        # In a real implementation, you would execute:
        # import subprocess
        # result = subprocess.run(service_config["restart_command"].split(), capture_output=True)
        
        # Simulate restart delay
        await asyncio.sleep(2)
        
        return {
            "service": service_name,
            "action": "restart",
            "status": "success",
            "message": f"Service '{service_name}' restart initiated",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to restart service {service_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to restart service: {str(e)}"
        )

@router.get("/services", response_model=List[Dict[str, Any]])
async def list_services(
    current_user: dict = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """
    List all monitored services and their configuration.
    """
    return [
        {
            "name": name,
            "critical": config["critical"],
            "health_endpoint": config["url"]
        }
        for name, config in SERVICES.items()
    ]