from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_pass_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_pass(plain_pass: str, hashed_pass:str) -> bool:
    return pwd_context.verify(plain_pass, hashed_pass)