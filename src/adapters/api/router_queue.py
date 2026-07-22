from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import date, time
from typing import List, Optional

from src.adapters.api.dependencies import get_db, get_current_user_claims, require_role
from src.adapters.db.repositories import SQLAlchemyAppointmentRepository
from src.services.queue_service import QueueService
from src.domain.models.user import UserRole
from src.domain.models.appointment import Appointment

router = APIRouter(prefix="/api/queue", tags=["Queue & Appointments"])

class BookAppointmentRequest(BaseModel):
    patient_id: str
    doctor_id: str
    appointment_date: date
    scheduled_time: time
    visit_type: str
    consultation_type: str
    notes: Optional[str] = ""

@router.post("/book", response_model=Appointment)
def book_appointment(
    req: BookAppointmentRequest,
    db: Session = Depends(get_db),
    claims: dict = Depends(require_role([UserRole.ADMIN, UserRole.RECEPTIONIST]))
):
    tenant_id = claims["tenant_id"]
    branch_id = claims["branch_id"]
    
    appt_repo = SQLAlchemyAppointmentRepository(db)
    queue_service = QueueService(appt_repo)
    
    try:
        appt = queue_service.book_appointment(
            tenant_id=tenant_id,
            branch_id=branch_id,
            patient_id=req.patient_id,
            doctor_id=req.doctor_id,
            appointment_date=req.appointment_date,
            scheduled_time=req.scheduled_time,
            visit_type=req.visit_type,
            consultation_type=req.consultation_type,
            notes=req.notes
        )
        return appt
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/{appointment_id}/checkin", response_model=Appointment)
def check_in(
    appointment_id: str,
    db: Session = Depends(get_db),
    claims: dict = Depends(require_role([UserRole.ADMIN, UserRole.RECEPTIONIST]))
):
    tenant_id = claims["tenant_id"]
    appt_repo = SQLAlchemyAppointmentRepository(db)
    queue_service = QueueService(appt_repo)
    try:
        return queue_service.check_in_patient(appointment_id, tenant_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/{appointment_id}/start-consult", response_model=Appointment)
def start_consult(
    appointment_id: str,
    db: Session = Depends(get_db),
    claims: dict = Depends(require_role([UserRole.ADMIN, UserRole.DOCTOR]))
):
    tenant_id = claims["tenant_id"]
    appt_repo = SQLAlchemyAppointmentRepository(db)
    queue_service = QueueService(appt_repo)
    try:
        return queue_service.start_consultation(appointment_id, tenant_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/live", response_model=List[Appointment])
def get_live_queue(
    query_date: Optional[date] = None,
    db: Session = Depends(get_db),
    claims: dict = Depends(get_current_user_claims)
):
    tenant_id = claims["tenant_id"]
    branch_id = claims["branch_id"]
    appt_repo = SQLAlchemyAppointmentRepository(db)
    queue_service = QueueService(appt_repo)
    return queue_service.get_live_queue(tenant_id, branch_id, query_date)
