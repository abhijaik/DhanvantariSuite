from enum import Enum
from datetime import date, time, datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

class AppointmentStatus(str, Enum):
    BOOKED = "BOOKED"
    SCHEDULED = "SCHEDULED"
    IN_QUEUE = "IN_QUEUE"
    CONSULTING = "CONSULTING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"

class Appointment(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    branch_id: str
    patient_id: str
    doctor_id: str
    appointment_date: date
    scheduled_time: time
    status: AppointmentStatus
    queue_token: str
    visit_type: str
    consultation_type: str
    notes: Optional[str] = ""
    created_at: datetime
    updated_at: datetime
