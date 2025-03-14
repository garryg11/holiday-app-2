"""Add Department model and update User to use department_id

Revision ID: e6a4e969f198
Revises: 61bbd02a2917
Create Date: 2025-03-14 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision = 'e6a4e969f198'
down_revision = '61bbd02a2917'
branch_labels = None
depends_on = None

def upgrade():
    # Get current connection and inspector.
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    tables = inspector.get_table_names()
    
    # Create the "department" table if it doesn't exist.
    if 'department' not in tables:
        op.create_table(
            'department',
            sa.Column('id', sa.Integer, primary_key=True),
            sa.Column('name', sa.String(100), nullable=False, unique=True),
            sa.Column('description', sa.String(250), nullable=True)
        )
    
    # Check if "department_id" column exists in "user" table.
    user_columns = [col['name'] for col in inspector.get_columns('user')]
    if 'department_id' not in user_columns:
        with op.batch_alter_table('user', schema=None) as batch_op:
            batch_op.add_column(sa.Column('department_id', sa.Integer, nullable=True))
    
    # Create the foreign key constraint outside the batch block.
    op.create_foreign_key(
        'fk_user_department_id',   # Constraint name
        source_table='user',        # Source table name
        referent_table='department',# Referenced table name
        local_cols=['department_id'], 
        remote_cols=['id']
    )

def downgrade():
    # Drop the foreign key constraint from "user" table.
    op.drop_constraint('fk_user_department_id', 'user', type_='foreignkey')
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_column('department_id')
    op.drop_table('department')
