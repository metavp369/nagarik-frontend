from fastapi import FastAPI, APIRouter, Request
from fastapi.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import asyncpg
import logging
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
import uuid
from datetime import datetime, timezone
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.core.config import settings
from app.core.rate_limiter import limiter
from app.core.security_headers import SecurityHeadersMiddleware
from app.api import api_router as domain_api_router
from app.services.escalation_scheduler import start_scheduler, stop_scheduler
from app.services.notification_worker import start_notification_worker, stop_notification_worker
from app.services.baseline_scheduler import start_baseline_scheduler, stop_baseline_scheduler
from app.services.behavior_ai import start_behavior_scheduler, stop_behavior_scheduler
from app.services.digital_twin_builder import start_twin_builder_scheduler, stop_twin_builder_scheduler
from app.services.predictive_engine import start_prediction_scheduler, stop_prediction_scheduler
from app.services.risk_learning_scheduler import start_risk_learning_scheduler, stop_risk_learning_scheduler
from app.services.dynamic_risk_scheduler import start_dynamic_risk_scheduler, stop_dynamic_risk_scheduler
from app.services.forecast_prewarm_scheduler import start_forecast_prewarm_scheduler, stop_forecast_prewarm_scheduler

# MongoDB connection
client = AsyncIOMotorClient(settings.mongo_url)
db = client[settings.db_name]

# PostgreSQL connection pool (Neon)
pg_pool: Optional[asyncpg.Pool] = None

async def get_pg_pool() -> asyncpg.Pool:
    global pg_pool
    if pg_pool is None:
        pg_pool = await asyncpg.create_pool(
            settings.database_url,
            min_size=1,
            max_size=10,
            ssl='require'
        )
    return pg_pool

# Create the main app with docs under /api prefix for ingress routing
app = FastAPI(docs_url="/api/docs", redoc_url="/api/redoc", openapi_url="/api/openapi.json")

# Rate limiter setup
app.state.limiter = limiter

@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"error": "Too many requests. Please try again later."},
    )

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")


# Define Models
class StatusCheck(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class StatusCheckCreate(BaseModel):
    client_name: str

# Add your routes to the router instead of directly to app
@api_router.get("/")
async def root():
    return {"message": "Hello World"}

@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_dict = input.model_dump()
    status_obj = StatusCheck(**status_dict)
    
    doc = status_obj.model_dump()
    doc['timestamp'] = doc['timestamp'].isoformat()
    
    _ = await db.status_checks.insert_one(doc)
    return status_obj

@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    status_checks = await db.status_checks.find({}, {"_id": 0}).to_list(1000)
    
    for check in status_checks:
        if isinstance(check['timestamp'], str):
            check['timestamp'] = datetime.fromisoformat(check['timestamp'])
    
    return status_checks

# Health check endpoint for PostgreSQL (Neon)
@api_router.get("/health/db")
async def health_check_db():
    try:
        pool = await get_pg_pool()
        if pool is None:
            return {"status": "error", "message": "DATABASE_URL not configured"}
        
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {"status": "error", "message": str(e)}


@api_router.get("/system/cache-status")
async def cache_status():
    """Redis cache health check and status."""
    from app.services.redis_service import get_info
    return get_info()


@api_router.get("/system/osrm-status")
async def osrm_status():
    """OSRM routing engine health check."""
    from app.services.osrm_service import get_status
    return get_status()


@api_router.get("/system/forecast-cache-status")
async def forecast_cache_status():
    """Risk forecast cache monitoring."""
    from app.services.redis_service import get_all_forecast_keys, _forecast_mem_cache
    keys = get_all_forecast_keys()
    mem_entries = len(_forecast_mem_cache)
    return {
        "redis_keys": len(keys),
        "memory_entries": mem_entries,
        "ttl_seconds": 1800,
        "grid_cell_size_m": 250,
    }

# Include the router in the main app
app.include_router(api_router)

# Include domain API routers (users, seniors, devices)
app.include_router(domain_api_router, prefix="/api")

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=settings.cors_origins.split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.core.monitoring_middleware import MonitoringMiddleware
app.add_middleware(MonitoringMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(SlowAPIMiddleware)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
    global pg_pool
    if pg_pool:
        await pg_pool.close()
    stop_scheduler()
    stop_notification_worker()
    stop_baseline_scheduler()
    stop_behavior_scheduler()
    stop_risk_learning_scheduler()
    stop_dynamic_risk_scheduler()
    logger.info(f"{settings.app_name} shutdown complete")

@app.on_event("startup")
async def startup_db():
    logger.info(f"Starting {settings.app_name} in {settings.app_env} environment")
    await get_pg_pool()
    logger.info("PostgreSQL connection pool initialized")
    
    start_scheduler()
    start_notification_worker()
    start_baseline_scheduler()
    start_behavior_scheduler()
    start_twin_builder_scheduler()
    start_prediction_scheduler()
    start_risk_learning_scheduler()
    start_dynamic_risk_scheduler()
    start_forecast_prewarm_scheduler()

    # Start Redis Pub/Sub listener for real-time SSE broadcasts
    import asyncio
    from app.services.event_broadcaster import broadcaster
    loop = asyncio.get_event_loop()
    broadcaster.start_redis_listener(loop)
    logger.info("Redis Pub/Sub listener initialized for emergency broadcasts")
