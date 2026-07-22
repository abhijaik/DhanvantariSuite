from enum import Enum
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

class UserRole(str, Enum):
    ADMIN = "ADMIN"
    DOCTOR = "DOCTOR"
    RECEPTIONIST = "RECEPTIONIST"
    BILLING = "BILLING"
    SUPERDOC = "SUPERDOC"

class User(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    branch_id: str
    username: str
    password_hash: str
    full_name: str
    role: UserRole
    created_at: datetime
    updated_at: datetime
