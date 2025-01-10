"""Agrego tabla de Strategies

Revision ID: 7513f583e099
Revises: e78b052d4991
Create Date: 2025-01-10 10:33:14.500678

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7513f583e099'
down_revision: Union[str, None] = 'e78b052d4991'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
