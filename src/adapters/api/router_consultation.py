from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import date
from typing import List, Optional

from src.adapters.api.dependencies import get_db, require_role
from src.adapters.db.repositories import SQLAlchemyConsultationRepository, SQLAlchemyAppointmentRepository
from src.services.consultation_service import ConsultationService
from src.domain.models.user import UserRole
from src.domain.models.consultation import Consultation, PrescriptionItem

router = APIRouter(prefix="/api/consultations", tags=["Consultations"])

class ConsultationCompleteRequest(BaseModel):
    appointment_id: str
    symptoms: List[str]
    diagnosis: str
    prescription: List[PrescriptionItem]
    blood_pressure: Optional[str] = None
    weight: Optional[float] = None
    height: Optional[float] = None
    temperature: Optional[float] = None
    pulse_rate: Optional[int] = None
    follow_up_date: Optional[date] = None
    notes: Optional[str] = ""

@router.post("/complete", response_model=Consultation)
def complete_consultation(
    req: ConsultationCompleteRequest,
    db: Session = Depends(get_db),
    claims: dict = Depends(require_role([UserRole.ADMIN, UserRole.DOCTOR]))
):
    tenant_id = claims["tenant_id"]
    branch_id = claims["branch_id"]
    
    consultation_repo = SQLAlchemyConsultationRepository(db)
    appointment_repo = SQLAlchemyAppointmentRepository(db)
    consultation_service = ConsultationService(consultation_repo, appointment_repo)
    
    try:
        return consultation_service.complete_consultation(
            tenant_id=tenant_id,
            branch_id=branch_id,
            appointment_id=req.appointment_id,
            symptoms=req.symptoms,
            diagnosis=req.diagnosis,
            prescription=req.prescription,
            blood_pressure=req.blood_pressure,
            weight=req.weight,
            height=req.height,
            temperature=req.temperature,
            pulse_rate=req.pulse_rate,
            follow_up_date=req.follow_up_date,
            notes=req.notes
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/patient/{patient_id}/history", response_model=List[Consultation])
def get_patient_history(
    patient_id: str,
    db: Session = Depends(get_db),
    claims: dict = Depends(require_role([UserRole.ADMIN, UserRole.DOCTOR]))
):
    tenant_id = claims["tenant_id"]
    consultation_repo = SQLAlchemyConsultationRepository(db)
    appointment_repo = SQLAlchemyAppointmentRepository(db)
    consultation_service = ConsultationService(consultation_repo, appointment_repo)
    return consultation_service.get_patient_history(patient_id, tenant_id)
