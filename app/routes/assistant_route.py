from fastapi import APIRouter, Depends, HTTPException, Request, Response, Query
from app.config.database import get_db
from app.services.assistant_service import AssistantService
from sqlalchemy.ext.asyncio import AsyncSession as Session
from app.schemas.User_schemas import UserCreate, UserUpdate, UserPaginationResponse, UserResponse, AssistantNameIdResponse
import logging 
logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/add", response_model = UserResponse)
async def add_assistant(data: UserCreate, request: Request, db: Session = Depends(get_db)):
    user_id = request.state.user.user_id
    role = request.state.user.role
    if role != "admin":
        raise HTTPException(403, "You are not authorised to perform this operation")
    assistant = await AssistantService.create_assistant(db, user_id, data)
    return UserResponse.model_validate(assistant)


@router.put("/update/{assistant_id}", response_model = UserResponse)
async def update_assistant(data: UserUpdate, assistant_id: str, request: Request, db: Session = Depends(get_db)):
    user_id = request.state.user.user_id
    role = request.state.user.role
    if role != "admin":
        raise HTTPException(403, "You are not authorised to perform this operation")
    assistant = await AssistantService.update_assistant(db, assistant_id, data, request)
    return UserResponse.model_validate(assistant)


@router.get("/me", response_model = UserResponse)
async def get_me(request: Request, db: Session = Depends(get_db)):
    user_id = request.state.user.user_id
    assistant = await AssistantService.get_my_info(db, user_id)
    if not assistant:
        raise HTTPException(404, "Assistant data not found")
    return UserResponse.model_validate(assistant)

@router.post("/activate/{assistant_id}")
async def mark_activated(request: Request, assistant_id: str, db: Session = Depends(get_db)):
    role = request.state.user.role
    if role != "admin":
        raise HTTPException(403, "You don't have the required permissions to perform this operation.")
    return await AssistantService.mark_account_activated(db, assistant_id)

@router.post("/deactivate/{assistant_id}")
async def mark_deactivated(request: Request, assistant_id: str, db: Session = Depends(get_db)):
    role = request.state.user.role
    if role != "admin":
        raise HTTPException(403, "You don't have the required permissions to perform this operation.")
    return await AssistantService.mark_account_deactivated(db, assistant_id)

@router.get("/all", response_model=UserPaginationResponse)
async def get_all(
    request: Request, 
    page: int = Query(1, ge=1), 
    size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db) 
):
    user_id = request.state.user.user_id
    role = request.state.user.role
    if role != "admin":
        raise HTTPException(403, "You are not authorised to perform this operation")
    assistants, total_count = await AssistantService.get_all_paginated(db, user_id, page, size)
    if not assistants:
        raise HTTPException(status_code=404, detail="Assistant data not found")

    total_pages = (total_count + size - 1) // size

    return {
        "items": assistants,
        "total_count": total_count,
        "page": page,
        "size": size,
        "total_pages": total_pages
    }



@router.delete("/delete/{assistant_id}")
async def deleted_assistant_account(request: Request, assistant_id: str, db: Session = Depends(get_db)):
    role = request.state.user.role
    if role != "admin":
        raise HTTPException(403, "You don't have the required permissions to perform this operation.")
    return await AssistantService.delete_assistant_account_by_id(db, assistant_id)



# @router.post("/reassign-admin/{old_admin_id}/{new_admin_id}")
# async def assign_new_admin_to_assistant(request: Request, old_admin_id: str, new_admin_id: str, db: Session = Depends(get_db)):
#     if request.state.user.role != "admin":
#         raise HTTPException(403, "You don't have the required permission to perform this operation")
#     return await AssistantService.assign_new_admin_to_assistants(db, old_admin_id, new_admin_id)


@router.get("/allassistant/name/id/{admin_id}", response_model=list[AssistantNameIdResponse])
async def get_all_the_assistant_name_id(request: Request, admin_id: str, db: Session = Depends(get_db)):
    if request.state.user.role != "admin":
        raise HTTPException(403, "You don't have the required permission to perform this operation")
    assistants = await AssistantService.get_name_id(db, admin_id)
    return [AssistantNameIdResponse.model_validate(assistant) for assistant in assistants]

