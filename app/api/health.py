"""
Sprint 3: Health Check and Monitoring Endpoints
Provides comprehensive monitoring for all infrastructure components
"""
import time
import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from app.core.cache import get_cache
from app.core.circuit_breaker import get_all_circuit_stats
from app.core.database import get_database
from app.services.simplified_flow_service import simplified_flow

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["health"])

@router.get("/", summary="Basic Health Check")
async def health_check() -> Dict[str, Any]:
    """Basic health check endpoint"""
    return {
        "status": "healthy",
        "service": "PicArcade API",
        "version": "Sprint 3",
        "timestamp": time.time()
    }

@router.get("/detailed", summary="Detailed System Health")
async def detailed_health_check() -> Dict[str, Any]:
    """Comprehensive health check for all system components"""
    start_time = time.time()
    health_status = {
        "overall": "healthy",
        "timestamp": start_time,
        "components": {},
        "summary": {}
    }
    
    component_failures = 0
    total_components = 0
    
    # Check Cache (Redis)
    try:
        cache = await get_cache()
        cache_health = await cache.get_health()
        health_status["components"]["cache"] = cache_health
        total_components += 1
        
        if not cache_health.get("healthy", False):
            component_failures += 1
            
    except Exception as e:
        health_status["components"]["cache"] = {
            "status": "error",
            "healthy": False,
            "error": str(e)
        }
        component_failures += 1
        total_components += 1
    
    # Check Database (Supabase)
    try:
        database = await get_database()
        # Test database connection
        result = await database.fetch_one("SELECT 1 as test")
        health_status["components"]["database"] = {
            "status": "connected",
            "healthy": True,
            "test_query": bool(result)
        }
        total_components += 1
        
    except Exception as e:
        health_status["components"]["database"] = {
            "status": "error", 
            "healthy": False,
            "error": str(e)
        }
        component_failures += 1
        total_components += 1
    
    # Check Circuit Breakers
    try:
        circuit_stats = await get_all_circuit_stats()
        health_status["components"]["circuit_breakers"] = circuit_stats
        total_components += 1
        
        # Consider circuit breakers unhealthy if too many are open
        open_circuits = circuit_stats.get("open_circuits", 0)
        total_circuits = circuit_stats.get("total_circuits", 0)
        
        if total_circuits > 0 and (open_circuits / total_circuits) > 0.5:
            component_failures += 1
            
    except Exception as e:
        health_status["components"]["circuit_breakers"] = {
            "status": "error",
            "error": str(e)
        }
        component_failures += 1
        total_components += 1
    
    # Check Intent Classifier
    try:
        classifier_health = await simplified_flow.get_health()
        health_status["components"]["simplified_flow"] = classifier_health
        total_components += 1
        
        if not classifier_health.get("initialized", False):
            component_failures += 1
            
    except Exception as e:
        health_status["components"]["simplified_flow"] = {
            "status": "error",
            "error": str(e)
        }
        component_failures += 1
        total_components += 1
    
    # Calculate overall health
    processing_time = time.time() - start_time
    health_percentage = ((total_components - component_failures) / total_components * 100) if total_components > 0 else 0
    
    health_status["summary"] = {
        "health_percentage": round(health_percentage, 1),
        "healthy_components": total_components - component_failures,
        "total_components": total_components,
        "failed_components": component_failures,
        "processing_time_ms": round(processing_time * 1000, 2)
    }
    
    # Set overall status
    if component_failures == 0:
        health_status["overall"] = "healthy"
    elif component_failures < total_components:
        health_status["overall"] = "degraded"
    else:
        health_status["overall"] = "unhealthy"
    
    return health_status

@router.get("/cache", summary="Cache Health and Stats")
async def cache_health() -> Dict[str, Any]:
    """Get detailed cache health and performance metrics"""
    try:
        cache = await get_cache()
        health = await cache.get_health()
        
        # Add additional metrics
        health["cache_type"] = "Redis (Distributed)"
        health["provider"] = "Upstash"
        
        return health
        
    except Exception as e:
        logger.error(f"Cache health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Cache unhealthy: {str(e)}")

@router.get("/ready", summary="Readiness Check")
async def readiness_check() -> Dict[str, Any]:
    """Kubernetes/Docker readiness probe endpoint"""
    try:
        # Quick checks for essential services
        cache = await get_cache()
        database = await get_database()
        
        # Test cache
        await cache.get("readiness_test")
        
        # Test database
        await database.fetch_one("SELECT 1")
        
        return {
            "ready": True,
            "status": "ready",
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Service not ready: {str(e)}")

@router.get("/live", summary="Liveness Check")
async def liveness_check() -> Dict[str, Any]:
    """Kubernetes/Docker liveness probe endpoint"""
    return {
        "alive": True,
        "status": "alive",
        "timestamp": time.time()
    } 