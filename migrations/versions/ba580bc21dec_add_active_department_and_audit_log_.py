"""Add active, department, and audit log models

Revision ID: ba580bc21dec
Revises: 22ee396e5c25
Create Date: 2025-03-09 23:22:12.743609

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ba580bc21dec'
down_revision = '22ee396e5c25'
branch_labels = None
depends_on = None


def upgrade():
    # Step 1: Add 'active' as nullable, plus 'department' as is
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column('active', sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column('department', sa.String(length=100), nullable=True))

    # Step 2: Set existing rows to have active = 1
    op.execute("UPDATE user SET active = 1")

    # Step 3: Alter the 'active' column to be non-nullable
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.alter_column('active', nullable=False)


def downgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_column('department')
        batch_op.drop_column('active')
