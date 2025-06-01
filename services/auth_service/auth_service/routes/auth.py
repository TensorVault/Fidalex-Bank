from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from auth_service import schemas, services
from auth_service.database import get_db

router = APIRouter()

@router.post("/register")
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    return services.create_user(user, db)