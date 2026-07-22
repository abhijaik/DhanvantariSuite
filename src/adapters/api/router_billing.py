from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from pydantic import BaseModel
from decimal import Decimal
from typing import List, Optional

from src.adapters.api.dependencies import get_db, require_role
from src.adapters.db.repositories import (
    SQLAlchemyInvoiceRepository, SQLAlchemyPatientRepository, SQLAlchemyAppointmentRepository
)
from src.adapters.docgen.pdf_generator import PDFGeneratorAdapter
from src.services.billing_service import BillingService
from src.domain.models.user import UserRole
from src.domain.models.invoice import Invoice, InvoiceItem, PaymentMode, PaymentStatus

router = APIRouter(prefix="/api/billing", tags=["Billing & Invoicing"])

class CreateInvoiceRequest(BaseModel):
    appointment_id: str
    items: List[InvoiceItem]
    discount_amount: Decimal = Decimal("0.00")
    payment_mode: PaymentMode = PaymentMode.CASH
    payment_status: PaymentStatus = PaymentStatus.PENDING

class PayInvoiceRequest(BaseModel):
    payment_mode: PaymentMode

@router.post("/invoice", response_model=Invoice)
def create_invoice(
    req: CreateInvoiceRequest,
    db: Session = Depends(get_db),
    claims: dict = Depends(require_role([UserRole.ADMIN, UserRole.BILLING]))
):
    tenant_id = claims["tenant_id"]
    branch_id = claims["branch_id"]
    
    invoice_repo = SQLAlchemyInvoiceRepository(db)
    patient_repo = SQLAlchemyPatientRepository(db)
    appt_repo = SQLAlchemyAppointmentRepository(db)
    doc_gen = PDFGeneratorAdapter()
    
    billing_service = BillingService(invoice_repo, patient_repo, appt_repo, doc_gen)
    
    try:
        return billing_service.create_invoice(
            tenant_id=tenant_id,
            branch_id=branch_id,
            appointment_id=req.appointment_id,
            items=req.items,
            discount_amount=req.discount_amount,
            payment_mode=req.payment_mode,
            payment_status=req.payment_status
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/invoice/{invoice_id}/pay", response_model=Invoice)
def pay_invoice(
    invoice_id: str,
    req: PayInvoiceRequest,
    db: Session = Depends(get_db),
    claims: dict = Depends(require_role([UserRole.ADMIN, UserRole.BILLING]))
):
    tenant_id = claims["tenant_id"]
    
    invoice_repo = SQLAlchemyInvoiceRepository(db)
    patient_repo = SQLAlchemyPatientRepository(db)
    appt_repo = SQLAlchemyAppointmentRepository(db)
    doc_gen = PDFGeneratorAdapter()
    
    billing_service = BillingService(invoice_repo, patient_repo, appt_repo, doc_gen)
    try:
        return billing_service.record_payment(invoice_id, tenant_id, req.payment_mode)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/invoice/{invoice_id}/print")
def print_invoice(
    invoice_id: str,
    lang: str = "en",
    db: Session = Depends(get_db),
    claims: dict = Depends(require_role([UserRole.ADMIN, UserRole.BILLING, UserRole.DOCTOR, UserRole.RECEPTIONIST]))
):
    tenant_id = claims["tenant_id"]
    invoice_repo = SQLAlchemyInvoiceRepository(db)
    patient_repo = SQLAlchemyPatientRepository(db)
    appt_repo = SQLAlchemyAppointmentRepository(db)
    doc_gen = PDFGeneratorAdapter()
    
    billing_service = BillingService(invoice_repo, patient_repo, appt_repo, doc_gen)
    try:
        pdf_bytes = billing_service.generate_receipt_pdf(invoice_id, tenant_id, lang)
        return Response(content=pdf_bytes, media_type="application/pdf")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
