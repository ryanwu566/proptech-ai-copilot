"""add tax oracle repurchase fields

Revision ID: 202605270002
Revises: 202605270001
Create Date: 2026-05-27
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "202605270002"
down_revision: Union[str, None] = "202605270001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tax_oracle_assessments",
        sa.Column(
            "replacement_purchase_value",
            sa.Numeric(precision=14, scale=2),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "tax_oracle_assessments",
        sa.Column("is_self_use", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "tax_oracle_assessments",
        sa.Column("has_outstanding_tax_debt", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("tax_oracle_assessments", "has_outstanding_tax_debt")
    op.drop_column("tax_oracle_assessments", "is_self_use")
    op.drop_column("tax_oracle_assessments", "replacement_purchase_value")
