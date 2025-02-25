"""Agrego tabla de Strategies

Revision ID: 655fe125c058
Revises: b3cf8fb7db95
Create Date: 2025-01-10 10:39:51.279454

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '655fe125c058'
down_revision: Union[str, None] = 'b3cf8fb7db95'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('Strategies',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('Name', sa.String(), nullable=False),
    sa.Column('Description', sa.String(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('Strategies')
    # ### end Alembic commands ###
