import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from src.main import app
from src.adapters.api.dependencies import get_db
from src.adapters.db.orm_models import Base

# Setup in-memory SQLite database with StaticPool to share connection across sessions
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

# Apply the dependency override
app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(name="client", scope="module")
def fixture_client():
    # Create tables
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c
    Base.metadata.drop_all(bind=engine)

def test_full_patient_consultation_billing_flow(client):
    headers = {
        "X-Tenant-ID": "test-tenant-1",
        "X-Branch-ID": "test-branch-main"
    }

    # 1. Register a user (Receptionist)
    reg_user_resp = client.post(
        "/api/auth/register",
        json={
            "username": "receptionist_jane",
            "password": "securepassword123",
            "full_name": "Jane Doe",
            "role": "RECEPTIONIST"
        },
        headers=headers
    )
    assert reg_user_resp.status_code == 200, reg_user_resp.text
    
    # 2. Login to get token
    login_resp = client.post(
        "/api/auth/login",
        data={
            "username": "receptionist_jane",
            "password": "securepassword123"
        },
        headers=headers
    )
    assert login_resp.status_code == 200
    token_data = login_resp.json()
    auth_header = {"Authorization": f"Bearer {token_data['access_token']}"}
    auth_headers = {**headers, **auth_header}

    # 3. Register a Patient
    patient_resp = client.post(
        "/api/patients/register",
        json={
            "full_name": "Aarav Sharma",
            "mobile": "9876543210", # Raw mobile number
            "date_of_birth": "1992-08-20",
            "age": 34,
            "gender": "Male",
            "address": "Mumbai, Maharashtra"
        },
        headers=auth_headers
    )
    assert patient_resp.status_code == 200, patient_resp.text
    patient = patient_resp.json()
    assert patient["patient_number"] is not None
    assert patient["mobile_normalized"] == "+919876543210" # Indian default prefix applied

    # 4. Prevent Patient Duplicate Mobile Profile
    dup_patient_resp = client.post(
        "/api/patients/register",
        json={
            "full_name": "Aarav Sharma Duplicate",
            "mobile": "+91 98765 43210", # Matches normalized representation
            "date_of_birth": "1992-08-20",
            "age": 34,
            "gender": "Male",
            "address": "Mumbai, Maharashtra"
        },
        headers=auth_headers
    )
    assert dup_patient_resp.status_code == 400
    assert "already registered" in dup_patient_resp.json()["detail"]

    # 5. Register a Doctor
    reg_doc_resp = client.post(
        "/api/auth/register",
        json={
            "username": "doctor_singh",
            "password": "docpassword123",
            "full_name": "Dr. Vivek Singh",
            "role": "DOCTOR"
        },
        headers=headers
    )
    assert reg_doc_resp.status_code == 200
    doctor = reg_doc_resp.json()

    # 6. Book an Appointment
    appt_resp = client.post(
        "/api/queue/book",
        json={
            "patient_id": patient["id"],
            "doctor_id": doctor["id"],
            "appointment_date": "2026-07-20",
            "scheduled_time": "10:30:00",
            "visit_type": "New",
            "consultation_type": "OPD",
            "notes": "First check-up"
        },
        headers=auth_headers
    )
    assert appt_resp.status_code == 200, appt_resp.text
    appt = appt_resp.json()
    assert appt["queue_token"] == "T-01" # First token of the day

    # 7. Check-in the Patient (receptionist queue check-in)
    checkin_resp = client.post(
        f"/api/queue/{appt['id']}/checkin",
        headers=auth_headers
    )
    assert checkin_resp.status_code == 200
    assert checkin_resp.json()["status"] == "IN_QUEUE"

    # Log in as doctor
    doc_login_resp = client.post(
        "/api/auth/login",
        data={
            "username": "doctor_singh",
            "password": "docpassword123"
        },
        headers=headers
    )
    doc_token = doc_login_resp.json()["access_token"]
    doc_auth_headers = {**headers, "Authorization": f"Bearer {doc_token}"}

    # 8. Start Consultation
    start_consult_resp = client.post(
        f"/api/queue/{appt['id']}/start-consult",
        headers=doc_auth_headers
    )
    assert start_consult_resp.status_code == 200
    assert start_consult_resp.json()["status"] == "CONSULTING"

    # 9. Complete Consultation with Structured Prescription
    complete_resp = client.post(
        "/api/consultations/complete",
        json={
            "appointment_id": appt["id"],
            "symptoms": ["Dry Cough", "Mild Fever"],
            "diagnosis": "Seasonal Influenza",
            "prescription": [
                {
                    "medicine_name": "Paracetamol 500mg",
                    "dosage": "1-0-1",
                    "frequency": "After meals",
                    "duration": "3 days",
                    "food_relation": "After Food",
                    "instructions": "Drink plenty of warm water"
                },
                {
                    "medicine_name": "Cough Syrup 10ml",
                    "dosage": "0-0-1",
                    "frequency": "Before sleeping",
                    "duration": "5 days",
                    "food_relation": "Before Food"
                }
            ],
            "blood_pressure": "120/80",
            "weight": 70.5,
            "height": 175.2,
            "temperature": 98.6,
            "pulse_rate": 72,
            "follow_up_date": "2026-07-25",
            "notes": "Rest for 2 days. Avoid cold beverages."
        },
        headers=doc_auth_headers
    )
    assert complete_resp.status_code == 200, complete_resp.text
    consultation = complete_resp.json()
    assert len(consultation["prescription"]) == 2

    # Log in as Billing Staff
    reg_billing_resp = client.post(
        "/api/auth/register",
        json={
            "username": "billing_bob",
            "password": "billpassword123",
            "full_name": "Bob Smith",
            "role": "BILLING"
        },
        headers=headers
    )
    assert reg_billing_resp.status_code == 200
    billing_login = client.post(
        "/api/auth/login",
        data={
            "username": "billing_bob",
            "password": "billpassword123"
        },
        headers=headers
    )
    bill_token = billing_login.json()["access_token"]
    bill_auth_headers = {**headers, "Authorization": f"Bearer {bill_token}"}

    # 10. Generate Invoice (Billing Engine)
    invoice_resp = client.post(
        "/api/billing/invoice",
        json={
            "appointment_id": appt["id"],
            "items": [
                {
                    "description": "General Consultation Charge",
                    "quantity": 1,
                    "unit_price": 500.00,
                    "tax_rate": 18.00, # 18% GST
                    "total": 0.00 # Recalculated by service
                },
                {
                    "description": "Influenza Diagnostic Kit",
                    "quantity": 1,
                    "unit_price": 200.00,
                    "tax_rate": 5.00, # 5% GST
                    "total": 0.00
                }
            ],
            "discount_amount": 50.00,
            "payment_mode": "UPI",
            "payment_status": "PENDING"
        },
        headers=bill_auth_headers
    )
    assert invoice_resp.status_code == 200, invoice_resp.text
    invoice = invoice_resp.json()
    
    # Check Calculations:
    # Item 1 total: 500 + 18% = 590
    # Item 2 total: 200 + 5% = 210
    # Subtotal (before tax): 500 + 200 = 700
    # Tax: 90 + 10 = 100
    # Discount: 50
    # Grand Total: 700 + 100 - 50 = 750
    assert float(invoice["subtotal"]) == 700.00
    assert float(invoice["tax_amount"]) == 100.00
    assert float(invoice["discount_amount"]) == 50.00
    assert float(invoice["total_amount"]) == 750.00

    # 11. Complete Invoice Payment
    pay_resp = client.post(
        f"/api/billing/invoice/{invoice['id']}/pay",
        json={"payment_mode": "UPI"},
        headers=bill_auth_headers
    )
    assert pay_resp.status_code == 200
    assert pay_resp.json()["payment_status"] == "PAID"

    # 12. Retrieve PDF Invoice Receipt (Multi-lingual test)
    print_resp = client.get(
        f"/api/billing/invoice/{invoice['id']}/print?lang=mr", # Marathi language print request
        headers=bill_auth_headers
    )
    assert print_resp.status_code == 200
    assert print_resp.headers["content-type"] == "application/pdf"
    assert len(print_resp.content) > 1000 # Verify PDF contains binary bytes data

def test_superdoc_role_bypass(client):
    headers = {
        "X-Tenant-ID": "test-tenant-1",
        "X-Branch-ID": "test-branch-main"
    }

    # 1. Register a SUPERDOC user
    reg_sd_resp = client.post(
        "/api/auth/register",
        json={
            "username": "superdoc_jane",
            "password": "superpassword123",
            "full_name": "Dr. Jane Super",
            "role": "SUPERDOC"
        },
        headers=headers
    )
    assert reg_sd_resp.status_code == 200, reg_sd_resp.text
    sd_user = reg_sd_resp.json()

    # 2. Login
    login_resp = client.post(
        "/api/auth/login",
        data={
            "username": "superdoc_jane",
            "password": "superpassword123"
        },
        headers=headers
    )
    assert login_resp.status_code == 200
    token_data = login_resp.json()
    sd_auth_headers = {**headers, "Authorization": f"Bearer {token_data['access_token']}"}

    # 3. SuperDoc registers a Patient (Normally Receptionist/Admin only)
    patient_resp = client.post(
        "/api/patients/register",
        json={
            "full_name": "Siddharth Roy",
            "mobile": "9998887770",
            "date_of_birth": "1988-12-05",
            "age": 37,
            "gender": "Male",
            "address": "Pune, India"
        },
        headers=sd_auth_headers
    )
    assert patient_resp.status_code == 200, patient_resp.text
    patient = patient_resp.json()

    # 4. SuperDoc books an appointment (Normally Receptionist/Admin only)
    appt_resp = client.post(
        "/api/queue/book",
        json={
            "patient_id": patient["id"],
            "doctor_id": sd_user["id"],
            "appointment_date": "2026-07-20",
            "scheduled_time": "14:00:00",
            "visit_type": "New",
            "consultation_type": "OPD",
            "notes": "SuperDoc test consult"
        },
        headers=sd_auth_headers
    )
    assert appt_resp.status_code == 200, appt_resp.text
    appt = appt_resp.json()

    # 5. SuperDoc starts and completes consultation (Normally Doctor/Admin only)
    start_resp = client.post(
        f"/api/queue/{appt['id']}/start-consult",
        headers=sd_auth_headers
    )
    assert start_resp.status_code == 200

    complete_resp = client.post(
        "/api/consultations/complete",
        json={
            "appointment_id": appt["id"],
            "symptoms": ["Headache"],
            "diagnosis": "Stress",
            "prescription": [
                {
                    "medicine_name": "Aspirin",
                    "dosage": "1-0-0",
                    "frequency": "After lunch",
                    "duration": "1 day",
                    "food_relation": "After Food"
                }
            ],
            "blood_pressure": "118/75",
            "weight": 68.0,
            "height": 172.0,
            "temperature": 98.4,
            "pulse_rate": 68,
            "follow_up_date": "2026-07-27"
        },
        headers=sd_auth_headers
    )
    assert complete_resp.status_code == 200, complete_resp.text

