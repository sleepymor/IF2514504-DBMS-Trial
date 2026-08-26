import hashlib
import json
import secrets
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from mysql.connector import IntegrityError, MySQLConnection
from pydantic import BaseModel, EmailStr, Field

from bismillah_mbd.database import get_db

router = APIRouter(tags=["Auth"])

PBKDF2_ITERATIONS = 120_000


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(min_length=8)


class LoginRequest(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    preferences: dict | None
    created_at: datetime


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt.encode(), PBKDF2_ITERATIONS
    ).hex()
    return f"{salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt, digest = stored.split("$", 1)
    except ValueError:
        return False
    candidate = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt.encode(), PBKDF2_ITERATIONS
    ).hex()
    return secrets.compare_digest(candidate, digest)


def fetch_user(conn: MySQLConnection, user_id: int) -> dict:
    with conn.cursor(dictionary=True) as cur:
        cur.execute(
            "SELECT id, username, email, preferences, created_at FROM users WHERE id = %s",
            (user_id,),
        )
        user = cur.fetchone()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.post("/auth/register", response_model=UserResponse, status_code=201)
def register(payload: RegisterRequest, conn: MySQLConnection = Depends(get_db)):
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s)",
                (payload.username, payload.email, hash_password(payload.password)),
            )
            new_id = cur.lastrowid
        conn.commit()
    except IntegrityError as e:
        raise HTTPException(status_code=409, detail="Username or email already taken") from e
    return fetch_user(conn, new_id)


@router.post("/auth/login", response_model=UserResponse)
def login(payload: LoginRequest, conn: MySQLConnection = Depends(get_db)):
    with conn.cursor(dictionary=True) as cur:
        cur.execute(
            "SELECT id, username, email, password_hash, preferences, created_at "
            "FROM users WHERE username = %s OR email = %s",
            (payload.username, payload.username),
        )
        user = cur.fetchone()
    if user is None or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {k: v for k, v in user.items() if k != "password_hash"}


@router.get("/users/{user_id}", response_model=UserResponse)
def get_user(user_id: int, conn: MySQLConnection = Depends(get_db)):
    return fetch_user(conn, user_id)


@router.put("/users/{user_id}/preferences", response_model=UserResponse)
def set_preferences(user_id: int, preferences: dict, conn: MySQLConnection = Depends(get_db)):
    fetch_user(conn, user_id)
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE users SET preferences = %s WHERE id = %s",
            (json.dumps(preferences), user_id),
        )
    conn.commit()
    return fetch_user(conn, user_id)
