"""Initial migration"""
from alembic import op
import sqlalchemy as sa

revision = '0001'
down_revision = None

def upgrade():
    op.create_table('users',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('hashed_pw', sa.String(255), nullable=False),
        sa.Column('nickname', sa.String(100)),
        sa.Column('plan', sa.String(10), server_default='free'),
        sa.Column('is_active', sa.Boolean, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table('reconstruction_tasks',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id'), nullable=False),
        sa.Column('status', sa.String(20), server_default='pending'),
        sa.Column('progress', sa.Integer, server_default='0'),
        sa.Column('phase', sa.String(100)),
        sa.Column('error_msg', sa.Text),
        sa.Column('quality', sa.String(20), server_default='standard'),
        sa.Column('image_count', sa.Integer, server_default='0'),
        sa.Column('image_keys', sa.Text),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table('models_3d',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id'), nullable=False),
        sa.Column('name', sa.String(200)),
        sa.Column('stl_key', sa.String(500)),
        sa.Column('glb_key', sa.String(500)),
        sa.Column('thumbnail_key', sa.String(500)),
        sa.Column('is_watertight', sa.Boolean, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table('printer_devices',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id'), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('protocol', sa.String(30), nullable=False),
        sa.Column('host', sa.String(200), nullable=False),
        sa.Column('api_key', sa.String(500)),
        sa.Column('is_connected', sa.Boolean, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

def downgrade():
    op.drop_table('printer_devices')
    op.drop_table('models_3d')
    op.drop_table('reconstruction_tasks')
    op.drop_table('users')
