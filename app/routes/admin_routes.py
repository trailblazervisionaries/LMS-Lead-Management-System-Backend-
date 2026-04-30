from fastapi import APIRouter, Depends, HTTPException, Request, Response
from app.config.database import get_db
from app.services.admin_service import AdminService
from sqlalchemy.ext.asyncio import AsyncSession as Session
from app.schemas.User_schemas import UserCreate, UserUpdate, UserPaginationResponse, UserResponse
import logging 
logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/public/add", response_model = UserResponse)
async def add_admin(data: UserCreate, db: Session = Depends(get_db)):
    admin = await AdminService.create_admin(db, data)
    return UserResponse.model_validate(admin)

@router.put("/update", response_model = UserResponse)
async def updated_admin(data: UserUpdate, request: Request, db: Session = Depends(get_db)):
    user_id = request.state.user.user_id
    role = request.state.user.role
    if role != "admin":
        raise HTTPException(403, "You are not authorised to perform this operation")
    admin = await AdminService.update_admin(db, user_id, data)
    return UserResponse.model_validate(admin)



@router.get("/me", response_model = UserResponse)
async def get_me(request: Request, db: Session = Depends(get_db)):
    user_id = request.state.user.user_id
    admin = await AdminService.get_my_info(db, user_id)
    if not admin:
        raise HTTPException(404, "Assistant data not found")
    return UserResponse.model_validate(admin)







