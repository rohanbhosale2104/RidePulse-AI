"""
Authentication routes: register & login using Motor + bcrypt + JWT.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.security import create_access_token, hash_password, verify_password
from app.database.connection import get_database
from app.schemas.auth_schema import TokenSchema, UserLoginSchema, UserRegisterSchema
from app.services import db_service

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenSchema, status_code=status.HTTP_201_CREATED)
async def register(
    payload: UserRegisterSchema, db: AsyncIOMotorDatabase = Depends(get_database)
):
    existing_username = await db_service.get_user_by_username(db, payload.username)
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Username already taken"
        )

    existing_email = await db_service.get_user_by_email(db, payload.email)
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
        )

    user_doc = {
        "username": payload.username,
        "email": payload.email,
        "full_name": payload.full_name,
        "hashed_password": hash_password(payload.password),
    }
    user_id = await db_service.create_user(db, user_doc)

    token = create_access_token(
        data={"sub": payload.username, "user_id": user_id, "email": payload.email}
    )
    return TokenSchema(access_token=token, username=payload.username, user_id=user_id)


@router.post("/login", response_model=TokenSchema)
async def login(
    payload: UserLoginSchema, db: AsyncIOMotorDatabase = Depends(get_database)
):
    user = await db_service.get_user_by_username(db, payload.username)
    if not user or not verify_password(payload.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    token = create_access_token(
        data={
            "sub": user["username"],
            "user_id": str(user["_id"]),
            "email": user["email"],
        }
    )
    return TokenSchema(
        access_token=token, username=user["username"], user_id=str(user["_id"])
    )
