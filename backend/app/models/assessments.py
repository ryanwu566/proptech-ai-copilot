from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Integer, JSON, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AegisCreditAssessment(Base):
    __tablename__ = "aegis_credit_assessments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    applicant_name: Mapped[str] = mapped_column(String(120), nullable=False)
    property_address: Mapped[str] = mapped_column(String(255), nullable=False)
    property_value: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    loan_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    monthly_income: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    existing_debt: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    loan_term_years: Mapped[int] = mapped_column(Integer, nullable=False)
    mock_result: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )


class TaxOracleAssessment(Base):
    __tablename__ = "tax_oracle_assessments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    taxpayer_name: Mapped[str] = mapped_column(String(120), nullable=False)
    property_address: Mapped[str] = mapped_column(String(255), nullable=False)
    assessed_value: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    replacement_purchase_value: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
        default=Decimal("0"),
    )
    annual_rental_income: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    holding_years: Mapped[int] = mapped_column(Integer, nullable=False)
    transaction_type: Mapped[str] = mapped_column(String(40), nullable=False)
    is_self_use: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    has_outstanding_tax_debt: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    mock_result: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )


class LexPropAssessment(Base):
    __tablename__ = "lex_prop_assessments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_name: Mapped[str] = mapped_column(String(120), nullable=False)
    property_address: Mapped[str] = mapped_column(String(255), nullable=False)
    title_number: Mapped[str] = mapped_column(String(80), nullable=False)
    has_lien: Mapped[bool] = mapped_column(Boolean, nullable=False)
    has_easement: Mapped[bool] = mapped_column(Boolean, nullable=False)
    dispute_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    mock_result: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
