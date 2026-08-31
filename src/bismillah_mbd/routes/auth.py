import hashlib
import json
import secrets
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from mysql.connector import Error as MySQLError, IntegrityError, MySQLConnection
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
    try:
        with conn.cursor(dictionary=True) as cur:
            cur.callproc("sp_get_user_by_id", (user_id,))
            for result in cur.stored_results():
                user = result.fetchone()
                break
            else:
                user = None
    except MySQLError as e:
        if e.errno == 1305:
            raise HTTPException(
                status_code=501,
                detail="sp_get_user_by_id does not exist yet - see src/bismillah_mbd/sql/03-procedures.sql",
            ) from e
        raise
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.post("/auth/register", response_model=UserResponse, status_code=201)
def register(payload: RegisterRequest, conn: MySQLConnection = Depends(get_db)):
    try:
        with conn.cursor() as cur:
            cur.callproc("sp_create_user", (
                payload.username,
                payload.email,
                hash_password(payload.password),
            ))
            for result in cur.stored_results():
                row = result.fetchone()
                if row:
                    new_id = row[0]
                    break
            else:
                new_id = cur.lastrowid
        conn.commit()
    except IntegrityError as e:
        raise HTTPException(status_code=409, detail="Username or email already taken") from e
    except MySQLError as e:
        if e.errno == 1305:
            raise HTTPException(
                status_code=501,
                detail="sp_create_user does not exist yet - see src/bismillah_mbd/sql/03-procedures.sql",
            ) from e
        raise
    return fetch_user(conn, new_id)


@router.post("/auth/login", response_model=UserResponse)
def login(payload: LoginRequest, conn: MySQLConnection = Depends(get_db)):
    try:
        with conn.cursor(dictionary=True) as cur:
            cur.callproc("sp_get_user_by_credentials", (payload.username,))
            for result in cur.stored_results():
                user = result.fetchone()
                break
            else:
                user = None
    except MySQLError as e:
        if e.errno == 1305:
            raise HTTPException(
                status_code=501,
                detail="sp_get_user_by_credentials does not exist yet - see src/bismillah_mbd/sql/03-procedures.sql",
            ) from e
        raise
    if user is None or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {k: v for k, v in user.items() if k != "password_hash"}


@router.get("/users/{user_id}", response_model=UserResponse)
def get_user(user_id: int, conn: MySQLConnection = Depends(get_db)):
    return fetch_user(conn, user_id)


@router.put("/users/{user_id}/preferences", response_model=UserResponse)
def set_preferences(user_id: int, preferences: dict, conn: MySQLConnection = Depends(get_db)):
    fetch_user(conn, user_id)
    try:
        with conn.cursor() as cur:
            cur.callproc("sp_update_user_preferences", (user_id, json.dumps(preferences)))
        conn.commit()
    except MySQLError as e:
        if e.errno == 1305:
            raise HTTPException(
                status_code=501,
                detail="sp_update_user_preferences does not exist yet - see src/bismillah_mbd/sql/03-procedures.sql",
            ) from e
        raise
    return fetch_user(conn, user_id)
