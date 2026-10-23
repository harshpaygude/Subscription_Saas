"""Azure connection and subscription records."""
from alembic import op
import sqlalchemy as sa

revision = "0002_azure_connections"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("azure_connections", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("platform_user_id", sa.String(255), nullable=False), sa.Column("microsoft_home_account_id", sa.String(255)), sa.Column("microsoft_tenant_id", sa.String(255)), sa.Column("status", sa.String(40), nullable=False, server_default="connected"), sa.Column("encrypted_token_cache", sa.Text()), sa.Column("last_successful_refresh", sa.DateTime(timezone=True)))
    op.create_index("ix_azure_connection_user", "azure_connections", ["platform_user_id"])
    op.create_table("azure_subscriptions", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("connection_id", sa.Integer(), sa.ForeignKey("azure_connections.id", ondelete="CASCADE"), nullable=False), sa.Column("subscription_id", sa.String(64), nullable=False), sa.Column("display_name", sa.String(255), nullable=False), sa.Column("tenant_id", sa.String(255)), sa.Column("state", sa.String(50)), sa.Column("selected", sa.Boolean(), nullable=False, server_default=sa.false()), sa.Column("last_seen_at", sa.DateTime(timezone=True)), sa.UniqueConstraint("connection_id", "subscription_id", name="uq_azure_subscription"))
    op.create_unique_constraint("uq_azure_identity", "azure_connections", ["platform_user_id", "microsoft_home_account_id"])


def downgrade() -> None:
    op.drop_table("azure_subscriptions")
    op.drop_index("ix_azure_connection_user", table_name="azure_connections")
    op.drop_table("azure_connections")
