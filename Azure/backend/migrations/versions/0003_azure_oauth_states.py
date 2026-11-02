"""Durable, expiring, single-use OAuth state records."""
from alembic import op
import sqlalchemy as sa

revision = "0003_azure_oauth_states"
down_revision = "0002_azure_connections"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("azure_oauth_states", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("state_hash", sa.String(64), nullable=False), sa.Column("platform_user_id", sa.String(255), nullable=False), sa.Column("encrypted_code_verifier", sa.Text(), nullable=False), sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False), sa.Column("consumed_at", sa.DateTime(timezone=True)))
    op.create_unique_constraint("uq_azure_oauth_state_hash", "azure_oauth_states", ["state_hash"])
    op.create_index("ix_azure_oauth_state_expiry", "azure_oauth_states", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_azure_oauth_state_expiry", table_name="azure_oauth_states")
    op.drop_table("azure_oauth_states")
