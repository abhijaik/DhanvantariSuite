import json
import uuid
from datetime import date, datetime
from typing import Optional, List
from sqlalchemy import select, func, or_
from sqlalchemy.orm import Session
from decimal import Decimal

from src.domain.models.user import User, UserRole
from src.domain.models.patient import Patient
from src.domain.models.appointment import Appointment, AppointmentStatus
from src.domain.models.consultation import Consultation, PrescriptionItem
from src.domain.models.invoice import Invoice, InvoiceItem, PaymentMode, PaymentStatus
from src.domain.models.sync_log import SyncLog, SyncOperation

from src.domain.ports.user_repository import UserRepository
from src.domain.ports.patient_repository import PatientRepository
from src.domain.ports.appointment_repository import AppointmentRepository
from src.domain.ports.consultation_repository import ConsultationRepository
from src.domain.ports.invoice_repository import InvoiceRepository
from src.domain.ports.sync_log_repository import SyncLogRepository

from src.adapters.db.orm_models import (
    UserORM, PatientORM, AppointmentORM, ConsultationORM, InvoiceORM, SyncLogORM
)

def _serialize_payload(obj):
    if hasattr(obj, 'isoformat'):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, (UserRole, AppointmentStatus, PaymentMode, PaymentStatus, SyncOperation)):
        return obj.value
    raise TypeError(f"Type {type(obj)} not serializable")

def _log_change(session: Session, table_name: str, record_id: str, operation: str, tenant_id: str, payload_dict: dict) -> None:
    payload_json = json.dumps(payload_dict, default=_serialize_payload)
    sync_log = SyncLogORM(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        table_name=table_name,
        record_id=record_id,
        operation=operation,
        payload=payload_json,
        timestamp=datetime.utcnow(),
        synced=False
    )
    session.add(sync_log)

# --- USER REPOSITORY ---
class SQLAlchemyUserRepository(UserRepository):
    def __init__(self, session: Session):
        self.session = session

    def save(self, user: User) -> User:
        # Check if user already exists
        orm = self.session.get(UserORM, user.id)
        operation = "UPDATE" if orm else "INSERT"
        
        if not orm:
            orm = UserORM(id=user.id)
            self.session.add(orm)
            
        orm.tenant_id = user.tenant_id
        orm.branch_id = user.branch_id
        orm.username = user.username
        orm.password_hash = user.password_hash
        orm.full_name = user.full_name
        orm.role = user.role.value
        
        self.session.flush() # Ensure DB state is up-to-date in transaction
        
        # Log transaction (CDC)
        payload = user.model_dump()
        payload.pop("password_hash", None) # Exclude sensitive data from sync log
        _log_change(self.session, "users", user.id, operation, user.tenant_id, payload)
        
        return user

    def find_by_id(self, user_id: str, tenant_id: str) -> Optional[User]:
        stmt = select(UserORM).where(UserORM.id == user_id, UserORM.tenant_id == tenant_id)
        orm = self.session.scalar(stmt)
        if not orm:
            return None
        return User(
            id=orm.id,
            tenant_id=orm.tenant_id,
            branch_id=orm.branch_id,
            username=orm.username,
            password_hash=orm.password_hash,
            full_name=orm.full_name,
            role=UserRole(orm.role),
            created_at=orm.created_at,
            updated_at=orm.updated_at
        )

    def find_by_username(self, username: str, tenant_id: str) -> Optional[User]:
        stmt = select(UserORM).where(UserORM.username == username, UserORM.tenant_id == tenant_id)
        orm = self.session.scalar(stmt)
        if not orm:
            return None
        return User(
            id=orm.id,
            tenant_id=orm.tenant_id,
            branch_id=orm.branch_id,
            username=orm.username,
            password_hash=orm.password_hash,
            full_name=orm.full_name,
            role=UserRole(orm.role),
            created_at=orm.created_at,
            updated_at=orm.updated_at
        )

    def list_by_branch(self, tenant_id: str, branch_id: str) -> List[User]:
        stmt = select(UserORM).where(UserORM.tenant_id == tenant_id, UserORM.branch_id == branch_id)
        result = self.session.scalars(stmt).all()
        return [
            User(
                id=orm.id,
                tenant_id=orm.tenant_id,
                branch_id=orm.branch_id,
                username=orm.username,
                password_hash=orm.password_hash,
                full_name=orm.full_name,
                role=UserRole(orm.role),
                created_at=orm.created_at,
                updated_at=orm.updated_at
            ) for orm in result
        ]

# --- PATIENT REPOSITORY ---
class SQLAlchemyPatientRepository(PatientRepository):
    def __init__(self, session: Session):
        self.session = session

    def save(self, patient: Patient) -> Patient:
        orm = self.session.get(PatientORM, patient.id)
        operation = "UPDATE" if orm else "INSERT"
        
        if not orm:
            orm = PatientORM(id=patient.id)
            self.session.add(orm)
            
        orm.tenant_id = patient.tenant_id
        orm.branch_id = patient.branch_id
        orm.patient_number = patient.patient_number
        orm.registration_date = patient.registration_date
        orm.full_name = patient.full_name
        orm.date_of_birth = patient.date_of_birth
        orm.age = patient.age
        orm.gender = patient.gender
        orm.mobile_normalized = patient.mobile_normalized
        orm.alternate_number = patient.alternate_number
        orm.email = patient.email
        orm.address = patient.address
        orm.blood_group = patient.blood_group
        orm.marital_status = patient.marital_status
        orm.emergency_contact = patient.emergency_contact
        orm.allergies = patient.allergies
        orm.medical_notes = patient.medical_notes
        
        self.session.flush()
        
        # Log CDC
        _log_change(self.session, "patients", patient.id, operation, patient.tenant_id, patient.model_dump())
        return patient

    def _to_domain(self, orm: PatientORM) -> Patient:
        return Patient(
            id=orm.id,
            tenant_id=orm.tenant_id,
            branch_id=orm.branch_id,
            patient_number=orm.patient_number,
            registration_date=orm.registration_date,
            full_name=orm.full_name,
            date_of_birth=orm.date_of_birth,
            age=orm.age,
            gender=orm.gender,
            mobile_normalized=orm.mobile_normalized,
            alternate_number=orm.alternate_number,
            email=orm.email,
            address=orm.address,
            blood_group=orm.blood_group,
            marital_status=orm.marital_status,
            emergency_contact=orm.emergency_contact,
            allergies=orm.allergies or "",
            medical_notes=orm.medical_notes or "",
            created_at=orm.created_at,
            updated_at=orm.updated_at
        )

    def find_by_id(self, patient_id: str, tenant_id: str) -> Optional[Patient]:
        stmt = select(PatientORM).where(PatientORM.id == patient_id, PatientORM.tenant_id == tenant_id)
        orm = self.session.scalar(stmt)
        if not orm:
            return None
        return self._to_domain(orm)

    def find_by_mobile(self, mobile_normalized: str, tenant_id: str) -> Optional[Patient]:
        stmt = select(PatientORM).where(PatientORM.mobile_normalized == mobile_normalized, PatientORM.tenant_id == tenant_id)
        orm = self.session.scalar(stmt)
        if not orm:
            return None
        return self._to_domain(orm)

    def search(self, query: str, tenant_id: str) -> List[Patient]:
        search_expr = f"%{query}%"
        stmt = select(PatientORM).where(
            PatientORM.tenant_id == tenant_id,
            or_(
                PatientORM.full_name.like(search_expr),
                PatientORM.mobile_normalized.like(search_expr),
                PatientORM.patient_number.like(search_expr)
            )
        )
        result = self.session.scalars(stmt).all()
        return [self._to_domain(orm) for orm in result]

# --- APPOINTMENT REPOSITORY ---
class SQLAlchemyAppointmentRepository(AppointmentRepository):
    def __init__(self, session: Session):
        self.session = session

    def save(self, appointment: Appointment) -> Appointment:
        orm = self.session.get(AppointmentORM, appointment.id)
        operation = "UPDATE" if orm else "INSERT"
        
        if not orm:
            orm = AppointmentORM(id=appointment.id)
            self.session.add(orm)
            
        orm.tenant_id = appointment.tenant_id
        orm.branch_id = appointment.branch_id
        orm.patient_id = appointment.patient_id
        orm.doctor_id = appointment.doctor_id
        orm.appointment_date = appointment.appointment_date
        orm.scheduled_time = appointment.scheduled_time
        orm.status = appointment.status.value
        orm.queue_token = appointment.queue_token
        orm.visit_type = appointment.visit_type
        orm.consultation_type = appointment.consultation_type
        orm.notes = appointment.notes
        
        self.session.flush()
        
        # Log CDC
        _log_change(self.session, "appointments", appointment.id, operation, appointment.tenant_id, appointment.model_dump())
        return appointment

    def _to_domain(self, orm: AppointmentORM) -> Appointment:
        return Appointment(
            id=orm.id,
            tenant_id=orm.tenant_id,
            branch_id=orm.branch_id,
            patient_id=orm.patient_id,
            doctor_id=orm.doctor_id,
            appointment_date=orm.appointment_date,
            scheduled_time=orm.scheduled_time,
            status=AppointmentStatus(orm.status),
            queue_token=orm.queue_token,
            visit_type=orm.visit_type,
            consultation_type=orm.consultation_type,
            notes=orm.notes or "",
            created_at=orm.created_at,
            updated_at=orm.updated_at
        )

    def find_by_id(self, appointment_id: str, tenant_id: str) -> Optional[Appointment]:
        stmt = select(AppointmentORM).where(AppointmentORM.id == appointment_id, AppointmentORM.tenant_id == tenant_id)
        orm = self.session.scalar(stmt)
        if not orm:
            return None
        return self._to_domain(orm)

    def list_by_date_and_doctor(self, appointment_date: date, doctor_id: str, tenant_id: str, branch_id: str) -> List[Appointment]:
        stmt = select(AppointmentORM).where(
            AppointmentORM.appointment_date == appointment_date,
            AppointmentORM.doctor_id == doctor_id,
            AppointmentORM.tenant_id == tenant_id,
            AppointmentORM.branch_id == branch_id
        ).order_by(AppointmentORM.scheduled_time)
        result = self.session.scalars(stmt).all()
        return [self._to_domain(orm) for orm in result]

    def list_queue(self, appointment_date: date, tenant_id: str, branch_id: str) -> List[Appointment]:
        stmt = select(AppointmentORM).where(
            AppointmentORM.appointment_date == appointment_date,
            AppointmentORM.tenant_id == tenant_id,
            AppointmentORM.branch_id == branch_id,
            AppointmentORM.status.in_([
                AppointmentStatus.IN_QUEUE.value,
                AppointmentStatus.CONSULTING.value,
                AppointmentStatus.SCHEDULED.value,
                AppointmentStatus.BOOKED.value
            ])
        ).order_by(AppointmentORM.scheduled_time)
        result = self.session.scalars(stmt).all()
        return [self._to_domain(orm) for orm in result]

    def get_next_token_value(self, appointment_date: date, doctor_id: str, tenant_id: str, branch_id: str) -> int:
        stmt = select(func.count(AppointmentORM.id)).where(
            AppointmentORM.appointment_date == appointment_date,
            AppointmentORM.doctor_id == doctor_id,
            AppointmentORM.tenant_id == tenant_id,
            AppointmentORM.branch_id == branch_id
        )
        count = self.session.scalar(stmt) or 0
        return count + 1

# --- CONSULTATION REPOSITORY ---
class SQLAlchemyConsultationRepository(ConsultationRepository):
    def __init__(self, session: Session):
        self.session = session

    def save(self, consultation: Consultation) -> Consultation:
        orm = self.session.get(ConsultationORM, consultation.id)
        operation = "UPDATE" if orm else "INSERT"
        
        if not orm:
            orm = ConsultationORM(id=consultation.id)
            self.session.add(orm)
            
        orm.tenant_id = consultation.tenant_id
        orm.branch_id = consultation.branch_id
        orm.appointment_id = consultation.appointment_id
        orm.patient_id = consultation.patient_id
        orm.doctor_id = consultation.doctor_id
        orm.symptoms = json.dumps(consultation.symptoms)
        orm.diagnosis = consultation.diagnosis
        orm.prescription_json = json.dumps([item.model_dump() for item in consultation.prescription])
        orm.blood_pressure = consultation.blood_pressure
        orm.weight = consultation.weight
        orm.height = consultation.height
        orm.temperature = consultation.temperature
        orm.pulse_rate = consultation.pulse_rate
        orm.follow_up_date = consultation.follow_up_date
        orm.notes = consultation.notes
        
        self.session.flush()
        
        # Log CDC
        _log_change(self.session, "consultations", consultation.id, operation, consultation.tenant_id, consultation.model_dump())
        return consultation

    def _to_domain(self, orm: ConsultationORM) -> Consultation:
        return Consultation(
            id=orm.id,
            tenant_id=orm.tenant_id,
            branch_id=orm.branch_id,
            appointment_id=orm.appointment_id,
            patient_id=orm.patient_id,
            doctor_id=orm.doctor_id,
            symptoms=json.loads(orm.symptoms),
            diagnosis=orm.diagnosis,
            prescription=[PrescriptionItem(**item) for item in json.loads(orm.prescription_json)],
            blood_pressure=orm.blood_pressure,
            weight=orm.weight,
            height=orm.height,
            temperature=orm.temperature,
            pulse_rate=orm.pulse_rate,
            follow_up_date=orm.follow_up_date,
            notes=orm.notes or "",
            created_at=orm.created_at,
            updated_at=orm.updated_at
        )

    def find_by_id(self, consultation_id: str, tenant_id: str) -> Optional[Consultation]:
        stmt = select(ConsultationORM).where(ConsultationORM.id == consultation_id, ConsultationORM.tenant_id == tenant_id)
        orm = self.session.scalar(stmt)
        if not orm:
            return None
        return self._to_domain(orm)

    def find_by_appointment_id(self, appointment_id: str, tenant_id: str) -> Optional[Consultation]:
        stmt = select(ConsultationORM).where(ConsultationORM.appointment_id == appointment_id, ConsultationORM.tenant_id == tenant_id)
        orm = self.session.scalar(stmt)
        if not orm:
            return None
        return self._to_domain(orm)

    def list_by_patient(self, patient_id: str, tenant_id: str) -> List[Consultation]:
        stmt = select(ConsultationORM).where(
            ConsultationORM.patient_id == patient_id,
            ConsultationORM.tenant_id == tenant_id
        ).order_by(ConsultationORM.created_at.desc())
        result = self.session.scalars(stmt).all()
        return [self._to_domain(orm) for orm in result]

# --- INVOICE REPOSITORY ---
class SQLAlchemyInvoiceRepository(InvoiceRepository):
    def __init__(self, session: Session):
        self.session = session

    def save(self, invoice: Invoice) -> Invoice:
        orm = self.session.get(InvoiceORM, invoice.id)
        operation = "UPDATE" if orm else "INSERT"
        
        if not orm:
            orm = InvoiceORM(id=invoice.id)
            self.session.add(orm)
            
        orm.tenant_id = invoice.tenant_id
        orm.branch_id = invoice.branch_id
        orm.appointment_id = invoice.appointment_id
        orm.invoice_number = invoice.invoice_number
        orm.items_json = json.dumps([item.model_dump() for item in invoice.items], default=_serialize_payload)
        orm.subtotal = invoice.subtotal
        orm.tax_amount = invoice.tax_amount
        orm.discount_amount = invoice.discount_amount
        orm.total_amount = invoice.total_amount
        orm.payment_mode = invoice.payment_mode.value
        orm.payment_status = invoice.payment_status.value
        
        self.session.flush()
        
        # Log CDC
        _log_change(self.session, "invoices", invoice.id, operation, invoice.tenant_id, invoice.model_dump())
        return invoice

    def find_by_id(self, invoice_id: str, tenant_id: str) -> Optional[Invoice]:
        stmt = select(InvoiceORM).where(InvoiceORM.id == invoice_id, InvoiceORM.tenant_id == tenant_id)
        orm = self.session.scalar(stmt)
        if not orm:
            return None
        return Invoice(
            id=orm.id,
            tenant_id=orm.tenant_id,
            branch_id=orm.branch_id,
            appointment_id=orm.appointment_id,
            invoice_number=orm.invoice_number,
            items=[InvoiceItem(**item) for item in json.loads(orm.items_json)],
            subtotal=orm.subtotal,
            tax_amount=orm.tax_amount,
            discount_amount=orm.discount_amount,
            total_amount=orm.total_amount,
            payment_mode=PaymentMode(orm.payment_mode),
            payment_status=PaymentStatus(orm.payment_status),
            created_at=orm.created_at,
            updated_at=orm.updated_at
        )

    def find_by_appointment_id(self, appointment_id: str, tenant_id: str) -> Optional[Invoice]:
        stmt = select(InvoiceORM).where(InvoiceORM.appointment_id == appointment_id, InvoiceORM.tenant_id == tenant_id)
        orm = self.session.scalar(stmt)
        if not orm:
            return None
        return Invoice(
            id=orm.id,
            tenant_id=orm.tenant_id,
            branch_id=orm.branch_id,
            appointment_id=orm.appointment_id,
            invoice_number=orm.invoice_number,
            items=[InvoiceItem(**item) for item in json.loads(orm.items_json)],
            subtotal=orm.subtotal,
            tax_amount=orm.tax_amount,
            discount_amount=orm.discount_amount,
            total_amount=orm.total_amount,
            payment_mode=PaymentMode(orm.payment_mode),
            payment_status=PaymentStatus(orm.payment_status),
            created_at=orm.created_at,
            updated_at=orm.updated_at
        )

    def find_by_invoice_number(self, invoice_number: str, tenant_id: str) -> Optional[Invoice]:
        stmt = select(InvoiceORM).where(InvoiceORM.invoice_number == invoice_number, InvoiceORM.tenant_id == tenant_id)
        orm = self.session.scalar(stmt)
        if not orm:
            return None
        return Invoice(
            id=orm.id,
            tenant_id=orm.tenant_id,
            branch_id=orm.branch_id,
            appointment_id=orm.appointment_id,
            invoice_number=orm.invoice_number,
            items=[InvoiceItem(**item) for item in json.loads(orm.items_json)],
            subtotal=orm.subtotal,
            tax_amount=orm.tax_amount,
            discount_amount=orm.discount_amount,
            total_amount=orm.total_amount,
            payment_mode=PaymentMode(orm.payment_mode),
            payment_status=PaymentStatus(orm.payment_status),
            created_at=orm.created_at,
            updated_at=orm.updated_at
        )

    def list_by_branch(self, tenant_id: str, branch_id: str) -> List[Invoice]:
        stmt = select(InvoiceORM).where(InvoiceORM.tenant_id == tenant_id, InvoiceORM.branch_id == branch_id).order_by(InvoiceORM.created_at.desc())
        result = self.session.scalars(stmt).all()
        return [
            Invoice(
                id=orm.id,
                tenant_id=orm.tenant_id,
                branch_id=orm.branch_id,
                appointment_id=orm.appointment_id,
                invoice_number=orm.invoice_number,
                items=[InvoiceItem(**item) for item in json.loads(orm.items_json)],
                subtotal=orm.subtotal,
                tax_amount=orm.tax_amount,
                discount_amount=orm.discount_amount,
                total_amount=orm.total_amount,
                payment_mode=PaymentMode(orm.payment_mode),
                payment_status=PaymentStatus(orm.payment_status),
                created_at=orm.created_at,
                updated_at=orm.updated_at
            ) for orm in result
        ]

# --- SYNC LOG REPOSITORY ---
class SQLAlchemySyncLogRepository(SyncLogRepository):
    def __init__(self, session: Session):
        self.session = session

    def save(self, sync_log: SyncLog) -> SyncLog:
        orm = self.session.get(SyncLogORM, sync_log.id)
        if not orm:
            orm = SyncLogORM(id=sync_log.id)
            self.session.add(orm)
            
        orm.tenant_id = sync_log.tenant_id
        orm.table_name = sync_log.table_name
        orm.record_id = sync_log.record_id
        orm.operation = sync_log.operation.value
        orm.payload = sync_log.payload
        orm.timestamp = sync_log.timestamp
        orm.synced = sync_log.synced
        
        self.session.flush()
        return sync_log

    def get_unsynced(self, tenant_id: str, limit: int = 100) -> List[SyncLog]:
        stmt = select(SyncLogORM).where(SyncLogORM.tenant_id == tenant_id, SyncLogORM.synced == False).order_by(SyncLogORM.timestamp.asc()).limit(limit)
        result = self.session.scalars(stmt).all()
        return [
            SyncLog(
                id=orm.id,
                tenant_id=orm.tenant_id,
                table_name=orm.table_name,
                record_id=orm.record_id,
                operation=SyncOperation(orm.operation),
                payload=orm.payload,
                timestamp=orm.timestamp,
                synced=orm.synced
            ) for orm in result
        ]

    def mark_as_synced(self, log_ids: List[str], tenant_id: str) -> None:
        if not log_ids:
            return
        stmt = select(SyncLogORM).where(SyncLogORM.id.in_(log_ids), SyncLogORM.tenant_id == tenant_id)
        orm_logs = self.session.scalars(stmt).all()
        for log in orm_logs:
            log.synced = True
        self.session.flush()
