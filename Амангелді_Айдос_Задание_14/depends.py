from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import User, get_session
from jose import JWTError, jwt
from auth import SECRET_KEY, ALGORITHM

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


async def get_current_user(
    token: str = Depends(oauth2_scheme), 
    session: AsyncSession = Depends(get_session)
):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get('sub')
        if username is None:
            raise HTTPException(status_code=401, detail="Unauthorized")
    except JWTError:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    query = select(User).where(User.username == username)
    res = await session.execute(query)
    user = res.scalar_one_or_none()

    if user is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    return user


def require_role(required_role: str):
    async def role_dependency(current_user: User = Depends(get_current_user)):
        if current_user.role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail='Permission error'
            )
        return current_user
    return role_dependency
