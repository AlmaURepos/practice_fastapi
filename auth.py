from datetime import datetime, timedelta
from typing import Optional
from jose import jwt
import os 

# SECRET_KEY="ae027ddda51bbf9a1570d6d5e66207ebbbd415ce91501c91113e92b1f9010c9de746d667ea1d6692f0992f56799c618f6f8841ac523c25ece9792cfe5f1183c7ac44ff82ca39c513381a5197f455db0a52a2932ee914cb8e2c7b7084c5d2712b78c78a28b7d85d0a7a20b94ce6178a10a5df043a3a3f90a4c24abfaf27bdaa3c14b5beff094bf61de9a5868786925bea470cc09c78e3de64b58af5d71eb3001da6866cfc5f4a320ef4f223e32022b7f7f76760ad20b4a8acd92a23b495199229623ce3343ed937b837dba52fa5ee2c69f54080d1495d872a8da90964f933f6cee3b2837404491bc3e0d6e51cf74547a9eb33289795c5b9f85efac3a85e77fde4"
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = 'HS256'
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None)->str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    return encoded_jwt