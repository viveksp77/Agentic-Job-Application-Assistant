import sqlite3
import os
from datetime import datetime, timedelta
from typing import Optional
from passlib.context import CryptContext
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel

SECRET_KEY = os.getenv('JWT_SECRET', 'jobagent-secret-key-change-in-production')
ALGORITHM  = 'HS256'
TOKEN_EXPIRE_HOURS = 24 * 7

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'applications.db')

pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
oauth2_scheme = OAuth2PasswordBearer(tokenUrl='/auth/login', auto_error=False)


def init_auth_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            email      TEXT    UNIQUE NOT NULL,
            username   TEXT    UNIQUE NOT NULL,
            password   TEXT    NOT NULL,
            created_at TEXT    NOT NULL
        )
    ''')
    try:
        conn.execute('ALTER TABLE applications ADD COLUMN user_id INTEGER')
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()


class UserCreate(BaseModel):
    email: str
    username: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = 'bearer'
    username: str
    email: str


def hash_password(password: str) -> str:
    return pwd_context.hash(password[:72])

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain[:72], hashed)

def create_token(user_id: int, username: str) -> str:
    payload = {'sub': str(user_id), 'username': username,
               'exp': datetime.utcnow() + timedelta(hours=TOKEN_EXPIRE_HOURS)}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None

def create_user(email: str, username: str, password: str) -> dict:
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            'INSERT INTO users (email, username, password, created_at) VALUES (?, ?, ?, ?)',
            (email.lower().strip(), username.strip(), hash_password(password), datetime.utcnow().isoformat())
        )
        conn.commit()
        user_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
        return {'id': user_id, 'email': email, 'username': username}
    except sqlite3.IntegrityError as e:
        if 'email' in str(e):
            raise HTTPException(status_code=400, detail='Email already registered.')
        raise HTTPException(status_code=400, detail='Username already taken.')
    finally:
        conn.close()

def get_user_by_username(username: str) -> Optional[dict]:
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        'SELECT id, email, username, password FROM users WHERE username = ?',
        (username.strip(),)
    ).fetchone()
    conn.close()
    return {'id': row[0], 'email': row[1], 'username': row[2], 'password': row[3]} if row else None

def authenticate_user(username: str, password: str) -> Optional[dict]:
    user = get_user_by_username(username)
    if not user or not verify_password(password, user['password']):
        return None
    return user

def get_current_user(token: str = Depends(oauth2_scheme)) -> Optional[dict]:
    if not token:
        return None
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail='Invalid or expired token.',
                            headers={'WWW-Authenticate': 'Bearer'})
    return {'id': int(payload['sub']), 'username': payload['username']}

def require_user(current_user: dict = Depends(get_current_user)) -> dict:
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail='Please log in.',
                            headers={'WWW-Authenticate': 'Bearer'})
    return current_user