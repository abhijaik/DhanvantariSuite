import uuid
from datetime import date, datetime
from typing import List, Optional

from src.domain.models.consultation import Consultation, PrescriptionItem
from src.domain.models.appointment import AppointmentStatus
from src.domain.ports.consultation_repository import ConsultationRepository
from src.domain.ports.appointment_repository import AppointmentRepository

class ConsultationService:
    def __init__(self, consultation_repo: ConsultationRepository, appointment_repo: AppointmentRepository):
        self.consultation_repo = consultation_repo
        self.appointment_repo = appointment_repo

    def complete_consultation(
        self,
        tenant_id: str,
        branch_id: str,
        appointment_id: str,
        symptoms: List[str],
        diagnosis: str,
        prescription: List[PrescriptionItem],
        blood_pressure: Optional[str] = None,
        weight: Optional[float] = None,
        height: Optional[float] = None,
        temperature: Optional[float] = None,
        pulse_rate: Optional[int] = None,
        follow_up_date: Optional[date] = None,
        notes: Optional[str] = ""
    ) -> Consultation:
        # Find corresponding appointment
        appointment = self.appointment_repo.find_by_id(appointment_id, tenant_id)
        if not appointment:
            raise ValueError("Appointment not found")

        # Create consultation
        consultation = Consultation(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            branch_id=branch_id,
            appointment_id=appointment_id,
            patient_id=appointment.patient_id,
            doctor_id=appointment.doctor_id,
            symptoms=symptoms,
            diagnosis=diagnosis,
            prescription=prescription,
            blood_pressure=blood_pressure,
            weight=weight,
            height=height,
            temperature=temperature,
            pulse_rate=pulse_rate,
            follow_up_date=follow_up_date,
            notes=notes,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        saved_consultation = self.consultation_repo.save(consultation)

        # Update appointment status to COMPLETED (which queues for billing)
        appointment.status = AppointmentStatus.COMPLETED
        appointment.updated_at = datetime.utcnow()
        self.appointment_repo.save(appointment)

        return saved_consultation

    def get_patient_history(self, patient_id: str, tenant_id: str) -> List[Consultation]:
        return self.consultation_repo.list_by_patient(patient_id, tenant_id)
