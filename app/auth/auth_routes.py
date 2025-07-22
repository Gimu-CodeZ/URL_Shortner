from fastapi import HTTPException, APIRouter
from passlib.context import CryptContext
from app.config import collection_user, db
from app.models.models import Users
from app.models.schemas import UserCreate, UserLogin   
from app.auth.jwt_handler import hash_password, verify_password, create_access_token

router = APIRouter()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

@router.post("/register")
async def register(user: UserCreate):
    # query = Users.select().where(Users.username == user.username)
    existing_user = collection_user.find_one({"username": user.username})
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")
    
    # Hash the password
    hashed_password = hash_password(user.password)

    # query = Users.insert().values(username=user.username, password_hash=hashed_password)
    collection_user.insert_one({"username": user.username, "password_hash": hashed_password})
    return {"message": "User registered successfully"}

@router.post("/login")
async def login(user: UserLogin):
    # query = Users.select().where(Users.username == user.username)
    existing_user = collection_user.find_one({"username": user.username})
    
    if not existing_user or not verify_password(user.password, existing_user["password_hash"]):
        raise HTTPException(status_code=400, detail="Invalid username or password")
    
    # Remove sensitive and problematic fields
    existing_user.pop("password_hash", None)
    if "_id" in existing_user:
        existing_user["_id"] = str(existing_user["_id"])
        
    access_token = create_access_token(data={"sub": existing_user["username"]})
    return {"access_token": access_token, "token_type": "bearer", "user": existing_user}

