from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import APIMiddleware
from app.config.database import create_tables
from fastapi.staticfiles import StaticFiles
from app.routes import (user_routes, admin_routes, assistant_route, lead_routes, form_routes, remark_routes, custom_mail_route, meeting_route, audit_routes)
import logging
from app.logging_config import setup_logging
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI()
app.add_middleware(APIMiddleware)
app.add_middleware(
    CORSMiddleware,
    # allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000", "http://127.0.0.1:3000"],  
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],  
    allow_headers=["*"],   
)

limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"]) # 100 requests per minute per user
app.state.limiter = limiter
#  Added Exception Handler to return 429 error to the client
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
# Added Middleware for automatic global enforcement
app.add_middleware(SlowAPIMiddleware)

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

@app.on_event("startup")
async def startup_event():
    logger.info("Application started 🚀")
    await create_tables()
    # logger.info("Scheduler started")

@app.get("/")
def health():
    return {"status": "FastAPI Scheduler Running"}

@app.get("/health")
def read_root():
    return {"message": "Welcome to Lead Management Backend :)"} 



# all the project user route
app.include_router(user_routes.router, prefix="/api/users", tags=["user"])
app.include_router(admin_routes.router, prefix="/api/admin", tags=["admin"])
app.include_router(assistant_route.router, prefix="/api/assistant", tags=["assistant"])
app.include_router(form_routes.router, prefix="/api/form", tags=["Lead-Form"])
app.include_router(lead_routes.router, prefix="/api/lead", tags=["lead"])
app.include_router(custom_mail_route.router, prefix="/api/custom", tags=["custom-mail"])
app.include_router(meeting_route.router, prefix="/api/meet", tags=["meeting"])
app.include_router(remark_routes.router, prefix="/api/remark", tags=["remarks"])
app.include_router(audit_routes.router, prefix="/api/audit", tags=["Audit"])


