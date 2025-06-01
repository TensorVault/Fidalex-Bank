from sqlalchemy.orm import Session
from auth_service.models import user as user_model
from auth_service.schemas import user as user_schema
from auth_service.utils import hashing

def create_user(user: user_schema.UserCreate, db: Session):
    hashed_pw = hashing.get_password_hash(user.password)
    db_user = user_model.User(username=user.username, email=user.email, hashed_password=hashed_pw)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user