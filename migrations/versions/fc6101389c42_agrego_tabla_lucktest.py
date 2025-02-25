"""Agrego tabla LuckTest

Revision ID: fc6101389c42
Revises: 899215aaff2f
Create Date: 2025-01-20 13:09:34.746578

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fc6101389c42'
down_revision: Union[str, None] = '899215aaff2f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('LuckTests',
    sa.Column('Id', sa.UUID(), nullable=False),
    sa.Column('BotPerformanceId', sa.UUID(), nullable=False),
    sa.Column('LuckTestPerformanceId', sa.UUID(), nullable=False),
    sa.Column('TradesPercentToRemove', sa.Float(), nullable=False),
    sa.ForeignKeyConstraint(['BotPerformanceId'], ['BotPerformances.Id'], ),
    sa.ForeignKeyConstraint(['LuckTestPerformanceId'], ['BotPerformances.Id'], ),
    sa.PrimaryKeyConstraint('Id')
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('LuckTests')
    # ### end Alembic commands ###
