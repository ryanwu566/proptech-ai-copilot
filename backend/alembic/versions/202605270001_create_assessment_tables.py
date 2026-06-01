"""create assessment tables

Revision ID: 202605270001
Revises:
Create Date: 2026-05-27
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "202605270001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "aegis_credit_assessments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("applicant_name", sa.String(length=120), nullable=False),
        sa.Column("property_address", sa.String(length=255), nullable=False),
        sa.Column("property_value", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("loan_amount", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("monthly_income", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("existing_debt", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("loan_term_years", sa.Integer(), nullable=False),
        sa.Column("mock_result", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_aegis_credit_assessments_created_at",
        "aegis_credit_assessments",
        ["created_at"],
    )

    op.create_table(
        "tax_oracle_assessments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("taxpayer_name", sa.String(length=120), nullable=False),
        sa.Column("property_address", sa.String(length=255), nullable=False),
        sa.Column("assessed_value", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("annual_rental_income", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("holding_years", sa.Integer(), nullable=False),
        sa.Column("transaction_type", sa.String(length=40), nullable=False),
        sa.Column("mock_result", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_tax_oracle_assessments_created_at",
        "tax_oracle_assessments",
        ["created_at"],
    )

    op.create_table(
        "lex_prop_assessments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_name", sa.String(length=120), nullable=False),
        sa.Column("property_address", sa.String(length=255), nullable=False),
        sa.Column("title_number", sa.String(length=80), nullable=False),
        sa.Column("has_lien", sa.Boolean(), nullable=False),
        sa.Column("has_easement", sa.Boolean(), nullable=False),
        sa.Column("dispute_notes", sa.Text(), nullable=True),
        sa.Column("mock_result", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_lex_prop_assessments_created_at",
        "lex_prop_assessments",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_lex_prop_assessments_created_at", table_name="lex_prop_assessments")
    op.drop_table("lex_prop_assessments")
    op.drop_index("ix_tax_oracle_assessments_created_at", table_name="tax_oracle_assessments")
    op.drop_table("tax_oracle_assessments")
    op.drop_index("ix_aegis_credit_assessments_created_at", table_name="aegis_credit_assessments")
    op.drop_table("aegis_credit_assessments")
