from fastapi import APIRouter, Depends, HTTPException, Request, Response, UploadFile, File, Form
from app.config.database import get_db
from app.services.admin_service import AdminService
from app.services.file_service import FileUploadService
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
    admin = await AdminService.update_admin(db, user_id, data, request)
    return UserResponse.model_validate(admin)

 

@router.get("/me", response_model = UserResponse)
async def get_me(request: Request, db: Session = Depends(get_db)):
    user_id = request.state.user.user_id
    admin = await AdminService.get_my_info(db, user_id)
    if not admin:
        raise HTTPException(404, "Admin data not found")
    return UserResponse.model_validate(admin)



@router.delete("/delete/{admin_id}")
async def deleted_assistant_account(request: Request, admin_id: str, db: Session = Depends(get_db)):
    role = request.state.user.role
    if role != "admin":
        raise HTTPException(403, "You don't have the required permissions to perform this operation.")
    return AdminService.delete_admin_account_by_id(db, admin_id)


@router.post("/upload-docs/{admin_id}")
async def upload_profile(
    request: Request,
    admin_id: str,
    name: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if request.state.user.role != "admin":
        raise HTTPException(403, "You do not have permission to perform this operation.")
    logged_user_id = request.state.user.user_id
    return await FileUploadService.upload_profile_image(db, file, logged_user_id, admin_id, name, request)

@router.get("/http://localhost:8000/api/admin/profile-image/abca2550924174/{admin_id}")
async def get_profile_image(
    request: Request,
    admin_id: str,
    db: Session = Depends(get_db),
):
    response = await FileUploadService.get_profile_image_buffer(db, request, admin_id)
    if not response:
        raise HTTPException(status_code=404, detail="Image not found in storage")
    return response



