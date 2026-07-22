from datetime import date, time, datetime
from typing import List, Optional
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, Date, Time, DateTime, Text, Numeric, Boolean, ForeignKey, UniqueConstraint, Integer, Float
from decimal import Decimal

class Base(DeclarativeBase):
    pass

class UserORM(Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("tenant_id", "username", name="uq_user_tenant_username"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), index=True)
    branch_id: Mapped[str] = mapped_column(String(36), index=True)
    username: Mapped[str] = mapped_column(String(50), index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class PatientORM(Base):
    __tablename__ = "patients"
    __table_args__ = (
        UniqueConstraint("tenant_id", "patient_number", name="uq_patient_tenant_number"),
        UniqueConstraint("tenant_id", "mobile_normalized", name="uq_patient_tenant_mobile"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), index=True)
    branch_id: Mapped[str] = mapped_column(String(36), index=True)
    patient_number: Mapped[str] = mapped_column(String(20), index=True)
    registration_date: Mapped[date] = mapped_column(Date)
    full_name: Mapped[str] = mapped_column(String(100))
    date_of_birth: Mapped[date] = mapped_column(Date)
    age: Mapped[int] = mapped_column(Integer)
    gender: Mapped[str] = mapped_column(String(10))
    mobile_normalized: Mapped[str] = mapped_column(String(15), index=True)
    alternate_number: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    address: Mapped[str] = mapped_column(Text)
    blood_group: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    marital_status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    emergency_contact: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    allergies: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    medical_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class AppointmentORM(Base):
    __tablename__ = "appointments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), index=True)
    branch_id: Mapped[str] = mapped_column(String(36), index=True)
    patient_id: Mapped[str] = mapped_column(String(36), ForeignKey("patients.id"))
    doctor_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"))
    appointment_date: Mapped[date] = mapped_column(Date, index=True)
    scheduled_time: Mapped[time] = mapped_column(Time)
    status: Mapped[str] = mapped_column(String(20))
    queue_token: Mapped[str] = mapped_column(String(10))
    visit_type: Mapped[str] = mapped_column(String(20))
    consultation_type: Mapped[str] = mapped_column(String(20))
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ConsultationORM(Base):
    __tablename__ = "consultations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), index=True)
    branch_id: Mapped[str] = mapped_column(String(36), index=True)
    appointment_id: Mapped[str] = mapped_column(String(36), ForeignKey("appointments.id"), unique=True)
    patient_id: Mapped[str] = mapped_column(String(36), ForeignKey("patients.id"))
    doctor_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"))
    symptoms: Mapped[str] = mapped_column(Text) # Stored as serialized JSON list
    diagnosis: Mapped[str] = mapped_column(Text)
    prescription_json: Mapped[str] = mapped_column(Text) # Stored as serialized JSON list of medicines
    blood_pressure: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    weight: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    height: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    temperature: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    pulse_rate: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    follow_up_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class InvoiceORM(Base):
    __tablename__ = "invoices"
    __table_args__ = (
        UniqueConstraint("tenant_id", "invoice_number", name="uq_invoice_tenant_number"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), index=True)
    branch_id: Mapped[str] = mapped_column(String(36), index=True)
    appointment_id: Mapped[str] = mapped_column(String(36), ForeignKey("appointments.id"), unique=True)
    invoice_number: Mapped[str] = mapped_column(String(20), index=True)
    items_json: Mapped[str] = mapped_column(Text) # Stored as serialized JSON array of line items
    subtotal: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    total_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    payment_mode: Mapped[str] = mapped_column(String(20))
    payment_status: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class SyncLogORM(Base):
    __tablename__ = "sync_transaction_log"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), index=True)
    table_name: Mapped[str] = mapped_column(String(50))
    record_id: Mapped[str] = mapped_column(String(36))
    operation: Mapped[str] = mapped_column(String(10))
    payload: Mapped[str] = mapped_column(Text) # Serialized JSON string of the record at the time of modification
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    synced: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
