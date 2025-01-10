"""elimino tabla de Strategies

Revision ID: b3cf8fb7db95
Revises: 7513f583e099
Create Date: 2025-01-10 10:36:23.843004

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b3cf8fb7db95'
down_revision: Union[str, None] = '7513f583e099'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
