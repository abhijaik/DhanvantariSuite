import pytest
from datetime import date, time, datetime
from decimal import Decimal
import uuid

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.adapters.db.orm_models import Base
from src.adapters.db.repositories import (
    SQLAlchemyUserRepository, SQLAlchemyPatientRepository, SQLAlchemyAppointmentRepository,
    SQLAlchemyConsultationRepository, SQLAlchemyInvoiceRepository, SQLAlchemySyncLogRepository
)
from src.domain.models.user import User, UserRole
from src.domain.models.patient import Patient
from src.domain.models.appointment import Appointment, AppointmentStatus
from src.domain.models.consultation import Consultation, PrescriptionItem
from src.domain.models.invoice import Invoice, InvoiceItem, PaymentMode, PaymentStatus
from src.domain.models.sync_log import SyncOperation

@pytest.fixture(name="db_session")
def fixture_db_session():
    # Use in-memory SQLite database for testing
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    
    # Enable foreign keys
    from sqlalchemy import event
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()

def test_user_repository_and_cdc(db_session):
    user_repo = SQLAlchemyUserRepository(db_session)
    sync_repo = SQLAlchemySyncLogRepository(db_session)
    
    user_id = str(uuid.uuid4())
    user = User(
        id=user_id,
        tenant_id="tenant-1",
        branch_id="branch-main",
        username="dr_smith",
        password_hash="hashed_pw",
        full_name="Dr. John Smith",
        role=UserRole.DOCTOR,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    # Save user (Should trigger CDC INSERT)
    saved_user = user_repo.save(user)
    db_session.commit()
    
    assert saved_user.username == "dr_smith"
    
    # Fetch from repository
    fetched_user = user_repo.find_by_id(user_id, "tenant-1")
    assert fetched_user is not None
    assert fetched_user.full_name == "Dr. John Smith"
    
    # Check CDC Log
    unsynced = sync_repo.get_unsynced("tenant-1")
    assert len(unsynced) == 1
    log = unsynced[0]
    assert log.table_name == "users"
    assert log.record_id == user_id
    assert log.operation == SyncOperation.INSERT
    assert "dr_smith" in log.payload
    assert "password_hash" not in log.payload # Sensitive info excluded

def test_patient_duplicate_prevention_and_token(db_session):
    patient_repo = SQLAlchemyPatientRepository(db_session)
    appt_repo = SQLAlchemyAppointmentRepository(db_session)
    
    # Save patient
    patient_id = str(uuid.uuid4())
    patient = Patient(
        id=patient_id,
        tenant_id="tenant-1",
        branch_id="branch-main",
        patient_number="P-10001",
        registration_date=date.today(),
        full_name="Rajesh Kumar",
        mobile_normalized="+919876543210",
        date_of_birth=date(1990, 5, 15),
        age=36,
        gender="Male",
        address="Pune, Maharashtra",
        blood_group="O+",
        marital_status="Married",
        emergency_contact="Jane Kumar",
        allergies="Peanuts",
        medical_notes="Hypertension history",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    patient_repo.save(patient)
    db_session.commit()
    
    # Try searching
    found = patient_repo.find_by_mobile("+919876543210", "tenant-1")
    assert found is not None
    assert found.full_name == "Rajesh Kumar"
    
    # Generate token
    token = appt_repo.get_next_token_value(date.today(), "doctor-1", "tenant-1", "branch-main")
    assert token == 1 # First token of the day for this doctor
