from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import date
from typing import List, Optional

from src.adapters.api.dependencies import get_db, get_current_user_claims, require_role
from src.adapters.db.repositories import SQLAlchemyPatientRepository
from src.services.patient_service import PatientService
from src.domain.models.user import UserRole
from src.domain.models.patient import Patient

router = APIRouter(prefix="/api/patients", tags=["Patients"])

class PatientRegisterRequest(BaseModel):
    full_name: str
    mobile: str
    date_of_birth: date
    age: int
    gender: str
    address: str
    registration_date: Optional[date] = None
    alternate_number: Optional[str] = None
    email: Optional[str] = None
    blood_group: Optional[str] = None
    marital_status: Optional[str] = None
    emergency_contact: Optional[str] = None
    allergies: Optional[str] = ""
    medical_notes: Optional[str] = ""

@router.post("/register", response_model=Patient)
def register_patient(
    req: PatientRegisterRequest,
    db: Session = Depends(get_db),
    claims: dict = Depends(require_role([UserRole.ADMIN, UserRole.RECEPTIONIST]))
):
    tenant_id = claims["tenant_id"]
    branch_id = claims["branch_id"]
    
    patient_repo = SQLAlchemyPatientRepository(db)
    patient_service = PatientService(patient_repo)
    
    try:
        patient = patient_service.register_patient(
            tenant_id=tenant_id,
            branch_id=branch_id,
            full_name=req.full_name,
            mobile=req.mobile,
            date_of_birth=req.date_of_birth,
            age=req.age,
            gender=req.gender,
            address=req.address,
            registration_date=req.registration_date,
            alternate_number=req.alternate_number,
            email=req.email,
            blood_group=req.blood_group,
            marital_status=req.marital_status,
            emergency_contact=req.emergency_contact,
            allergies=req.allergies,
            medical_notes=req.medical_notes
        )
        return patient
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/search", response_model=List[Patient])
def search_patients(
    q: str,
    db: Session = Depends(get_db),
    claims: dict = Depends(get_current_user_claims)
):
    tenant_id = claims["tenant_id"]
    patient_repo = SQLAlchemyPatientRepository(db)
    patient_service = PatientService(patient_repo)
    return patient_service.search_patients(q, tenant_id)
