"""cambio elimino risk de botperformance

Revision ID: e7be8fb2c516
Revises: 8bf9de6c661a
Create Date: 2025-01-15 10:57:59.295184

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e7be8fb2c516'
down_revision: Union[str, None] = '8bf9de6c661a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('BotPerformances', 'Risk')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('BotPerformances', sa.Column('Risk', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=False))
    # ### end Alembic commands ###
