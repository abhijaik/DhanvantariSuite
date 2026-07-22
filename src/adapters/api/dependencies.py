from typing import Generator, Tuple, Optional
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.orm import Session

from src.adapters.db.connection import get_db_session
from src.services.auth_service import SECRET_KEY, ALGORITHM
from src.domain.models.user import UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

def get_db() -> Generator[Session, None, None]:
    with get_db_session() as session:
        yield session

def get_tenant_context(
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),
    x_branch_id: Optional[str] = Header(None, alias="X-Branch-ID"),
    authorization: Optional[str] = Header(None)
) -> Tuple[str, str]:
    """
    Resolves the tenant_id and branch_id for the request.
    In local single-tenant desktop mode: defaults to 'local-clinic' and 'branch-main'.
    In cloud SaaS mode: reads headers or parses JWT.
    """
    tenant_id = x_tenant_id or "local-clinic"
    branch_id = x_branch_id or "branch-main"

    # If JWT is provided, extract tenant info from it
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            tenant_id = payload.get("tenant_id", tenant_id)
            branch_id = payload.get("branch_id", branch_id)
        except JWTError:
            pass # Fallback to header or default in case of invalid token during local debug

    return tenant_id, branch_id

def get_current_user_claims(
    token: Optional[str] = Depends(oauth2_scheme),
    context: Tuple[str, str] = Depends(get_tenant_context)
) -> dict:
    """Parses user claims from JWT. Fallbacks to default user in local offline dev mode."""
    tenant_id, branch_id = context
    
    if not token:
        # Local fallback context (for development/single-user desktop mode without auth)
        return {
            "user_id": "local-admin-id",
            "username": "local-admin",
            "role": UserRole.ADMIN.value,
            "tenant_id": tenant_id,
            "branch_id": branch_id
        }
        
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        username: str = payload.get("username")
        role: str = payload.get("role")
        token_tenant: str = payload.get("tenant_id")
        token_branch: str = payload.get("branch_id")
        
        if user_id is None or username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return {
            "user_id": user_id,
            "username": username,
            "role": role,
            "tenant_id": token_tenant or tenant_id,
            "branch_id": token_branch or branch_id
        }
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

def require_role(allowed_roles: list[UserRole]):
    def role_dependency(claims: dict = Depends(get_current_user_claims)):
        user_role = claims.get("role")
        if user_role == UserRole.SUPERDOC.value:
            return claims
        if user_role not in [role.value for role in allowed_roles]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this resource"
            )
        return claims
    return role_dependency
