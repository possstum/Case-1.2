"""application schema bootstrap"""

from alembic import op

from app.db import models  # noqa: F401
from app.db.base import Base

revision = "7f6b4e2c9a11"
down_revision = "4a5c6b7d8e9f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
