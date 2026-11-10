"""link vendor users to vendor records

Revision ID: 340fd9ccf140
Revises: 9c5d5f74150f
Create Date: 2026-10-01 19:28:33.348803

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '340fd9ccf140'
down_revision: Union[str, Sequence[str], None] = '9c5d5f74150f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "users",
        sa.Column(
            "vendor_id",
            sa.Integer(),
            nullable=True,
        ),
    )

    op.create_foreign_key(
        "fk_users_vendor_id_vendors",
        "users",
        "vendors",
        ["vendor_id"],
        ["id"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        "fk_users_vendor_id_vendors",
        "users",
        type_="foreignkey",
    )

    op.drop_column(
        "users",
        "vendor_id",
    )