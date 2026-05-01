from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from core.database import get_db
from core.authorization import get_current_user_full
from models.user import User
from services.memory_service import MemoryService

router = APIRouter(prefix="/memory", tags=["Memory"])

class MemoryRequest(BaseModel):
    content: str
    memory_type: str = "general"


@router.post("/store")
async def store_memory(
    request: MemoryRequest,
    current_user: User = Depends(get_current_user_full),
    db: Session = Depends(get_db)
):
    """Store a memory for the user's company"""
    memory = MemoryService.store_memory(
        db,
        request.content,
        request.memory_type,
        company_id=current_user.company_id
    )
    return {"message": "Memory stored successfully", "memory_id": memory.id}


@router.get("/search")
async def search_memory(
    query: str,
    limit: int = 3,
    current_user: User = Depends(get_current_user_full),
    db: Session = Depends(get_db)
):
    """Search memories by semantic similarity"""
    results = MemoryService.search_memory(
        db,
        query,
        limit,
        company_id=current_user.company_id
    )
    return {
        "data": [
            {"id": r.id, "content": r.content, "type": r.memory_type}
            for r in results
        ]
    }
