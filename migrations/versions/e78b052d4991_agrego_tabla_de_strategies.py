"""Agrego tabla de Strategies

Revision ID: e78b052d4991
Revises: 8bac0d8560c0
Create Date: 2025-01-10 10:21:25.045051

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e78b052d4991'
down_revision: Union[str, None] = '8bac0d8560c0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
