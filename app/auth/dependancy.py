from fastapi import HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer
from jwt_handler import decode_access_token

ouath3_shema = OAuth2PasswordBearer(tokenUrl="/login")

def get_current_user(token: str = Depends(ouath3_shema)):
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    username: str = payload.get("sub")
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return username

