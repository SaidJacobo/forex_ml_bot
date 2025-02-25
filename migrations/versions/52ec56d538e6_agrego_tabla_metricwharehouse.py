"""Agrego tabla MetricWharehouse

Revision ID: 52ec56d538e6
Revises: b29d5c70e310
Create Date: 2025-01-17 09:01:51.447633

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '52ec56d538e6'
down_revision: Union[str, None] = 'b29d5c70e310'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('MetricsWarehouse',
    sa.Column('Id', sa.UUID(), nullable=False),
    sa.Column('BotPerformanceId', sa.UUID(), nullable=False),
    sa.Column('Method', sa.String(), nullable=False),
    sa.Column('Metric', sa.String(), nullable=False),
    sa.Column('ColumnName', sa.String(), nullable=False),
    sa.Column('Value', sa.Float(), nullable=False),
    sa.ForeignKeyConstraint(['BotPerformanceId'], ['BotPerformances.Id'], ),
    sa.PrimaryKeyConstraint('Id')
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('MetricsWarehouse')
    # ### end Alembic commands ###
