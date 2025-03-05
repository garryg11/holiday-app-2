"""Add time_off_balance to User model

Revision ID: 9dbc045f113a
Revises: cf72f1627758
Create Date: 2025-03-05 22:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9dbc045f113a'
down_revision = 'cf72f1627758'
branch_labels = None
depends_on = None


def upgrade():
    # Step 1: Add the column as nullable
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column('time_off_balance', sa.Float(), nullable=True))
    
    # Step 2: Set the default value (20.0) for existing rows
    op.execute("UPDATE user SET time_off_balance = 20.0")
    
    # Step 3: Alter the column to be non-nullable now that all rows have a value
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.alter_column('time_off_balance', nullable=False)


def downgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_column('time_off_balance')

