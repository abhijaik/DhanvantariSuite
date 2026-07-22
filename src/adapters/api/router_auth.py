from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel

from src.adapters.api.dependencies import get_db, get_tenant_context
from src.adapters.db.repositories import SQLAlchemyUserRepository
from src.services.auth_service import AuthService
from src.domain.models.user import UserRole, User

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

class RegisterRequest(BaseModel):
    username: str
    password: str
    full_name: str
    role: UserRole

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    role: str

@router.post("/register", response_model=User)
def register(
    req: RegisterRequest,
    db: Session = Depends(get_db),
    context: tuple[str, str] = Depends(get_tenant_context)
):
    tenant_id, branch_id = context
    user_repo = SQLAlchemyUserRepository(db)
    auth_service = AuthService(user_repo)
    try:
        user = auth_service.register_user(
            tenant_id=tenant_id,
            branch_id=branch_id,
            username=req.username,
            password=req.password,
            full_name=req.full_name,
            role=req.role
        )
        return user
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/login", response_model=TokenResponse)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
    context: tuple[str, str] = Depends(get_tenant_context)
):
    tenant_id, branch_id = context
    user_repo = SQLAlchemyUserRepository(db)
    auth_service = AuthService(user_repo)
    
    user = auth_service.authenticate_user(tenant_id, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token carrying tenant, branch, and role context
    token_data = {
        "sub": user.id,
        "username": user.username,
        "role": user.role.value,
        "tenant_id": user.tenant_id,
        "branch_id": user.branch_id
    }
    access_token = auth_service.create_access_token(token_data)
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": user.role.value
    }
