# 🏥 DhanvantariSuite: Next-Gen Clinic ERP & Management System

DhanvantariSuite is a modern, highly scalable Clinic Management System (ERP) designed as a decoupled, offline-first Desktop/LAN application for single or multi-branch clinics. Built with a modular Hexagonal Architecture, the system is designed to transition seamlessly to a Web/SaaS-based cloud deployment in the future with zero business logic rewrites.

---

## 🚀 Key Features

* **🎭 Dynamic Role-Based Access Control (RBAC):**
  * **Admin:** System settings, branch management, auditing, doctor registration, and advanced reporting.
  * **Receptionist:** Patient registrations, scheduling appointments, and check-in processing.
  * **Doctor:** Patient queue management, clinical consulting history, and prescription entries.
  * **SuperDoc:** All-in-one clinician profile bypassing authorization boundaries to manage both clinic operations and consultations.
* **🩺 Expanded Patient Demographics:** Captures 15 standard clinical and demographic metrics (e.g., DOB-based age calculation, emergency contacts, drug/food allergies, and chronic notes) with automated international phone format normalization.
* **📅 Queue & Appointment Scheduling:** Generates daily incremental queue tokens (e.g., `T-01`, `T-02`) with visit type (`New`/`Follow-up`) and channel (`OPD`/`Online`) tagging.
* **📝 Clinical Consultation & Prescription Entry:** Supports detailed vital signs recording (BP, weight, height, temperature, pulse rate), follow-up date scheduling, and medicine specifications with before/after food dropdown options.
* **💵 Multilingual Billing & Invoicing:** Features dynamic billing line item entry, automatic GST/tax calculations, and multilingual PDF receipt generation supporting English, Hindi (हिंदी), and Marathi (मराठी) with proper Devanagari font rendering.
* **🔄 Offline-First Change Data Capture (CDC):** Intercepts all database transactions (INSERT/UPDATE/DELETE) and stores changes in a replica sync log table for batch-pull replication to a central cloud server.

---

## 🏗️ Architecture

The backend implements strict **Hexagonal Architecture** principles:

```
src/
├── domain/            # Domain Core (Pure Python models, Ports / Interfaces)
│   ├── models/        # Patient, Appointment, Consultation, User, Invoice
│   └── ports/         # Repository interfaces
├── services/          # Application services containing all business rules
├── adapters/          # Infrastructure Adapters (HTTP controllers, SQLAlchemy databases)
│   ├── db/            # SQLite repository implementations & ORM schemas
│   ├── api/           # FastAPI routers & RBAC middleware
│   └── docgen/        # Devanagari-compatible multi-lingual PDF generator
└── static/            # Glassmorphic responsive Single-Page Client UI
```

* **Zero-Rewrite Multi-Tenancy:** Every database table partitions records using `tenant_id` and `branch_id` from day one, facilitating a direct cloud SaaS upgrade.
* **Bcrypt Password Cryptography:** Native bcrypt hashing handles authentication securely, avoiding legacy dependency bugs.
* **StaticPool Connection Isolation:** High-speed SQLite configuration utilizing `poolclass=StaticPool` for integration testing.

---

## 💻 UI Design Aesthetics

The user interface is a dark-theme, responsive single-page dashboard built with modern glassmorphism design parameters:
* Dynamic tab visibility governed by authenticated user role claims.
* Interactive vitals grid and automated calculation widgets.
* Visual tag badges on queue tables for quick categorizations.
* Quick-connect debug triggers for instant test-profile authentication.

---

## 🛠️ Quick Start & Installation

### Prerequisites
* Python 3.11+
* Chrome or any WebKit-compatible browser

### Setup Virtual Environment
```bash
# Clone the repository
git clone https://github.com/abhijaik/DhanvantariSuite.git
cd DhanvantariSuite

# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate      # On Windows
source venv/bin/activate    # On Linux/macOS

# Install dependencies
pip install -r requirements.txt
```

### Running the Application
To run the server in developer/API server mode:
```bash
python -m uvicorn src.main:app --reload --port 8000
```
Then navigate to `http://127.0.0.1:8000/ui/index.html` in your browser.

To run the native desktop shell wrapper:
```bash
python desktop/desktop_shell.py
```

### Running Test Suite
Execute the pytest integration test suite to verify route authorization and database mappings:
```bash
python -m pytest
```

---

## 👥 Seeded Test Credentials
The database seeds default profiles automatically on startup:
* **Admin:** `admin_user` / `adminpass123`
* **Receptionist:** `receptionist_user` / `receppass123`
* **Doctor:** `doctor_user` / `docpass123`
* **SuperDoc:** `superdoc_user` / `superpass123`
