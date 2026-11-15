"""LSK finance reconciliation baseline."""
from alembic import op
import sqlalchemy as sa
revision="0001_initial"
down_revision=None
branch_labels=None
depends_on=None

def upgrade():
    op.create_table("finance_records",
      sa.Column("id",sa.String(36),primary_key=True),
      sa.Column("tenant_id",sa.String(100),nullable=False),
      sa.Column("source",sa.String(20),nullable=False),
      sa.Column("external_id",sa.String(100),nullable=False),
      sa.Column("reference",sa.String(100),nullable=False),
      sa.Column("amount",sa.Numeric(18,2),nullable=False),
      sa.Column("currency",sa.String(3),nullable=False),
      sa.UniqueConstraint("tenant_id","source","external_id"))
    op.create_index("ix_finance_records_tenant_id","finance_records",["tenant_id"])
    op.create_index("ix_finance_records_reference","finance_records",["reference"])
    op.create_table("reconciliations",
      sa.Column("id",sa.String(36),primary_key=True),
      sa.Column("tenant_id",sa.String(100),nullable=False),
      sa.Column("reference",sa.String(100),nullable=False),
      sa.Column("status",sa.String(30),nullable=False),
      sa.Column("details",sa.String(300),nullable=False),
      sa.UniqueConstraint("tenant_id","reference"))
    op.create_index("ix_reconciliations_tenant_id","reconciliations",["tenant_id"])

def downgrade():
    op.drop_index("ix_reconciliations_tenant_id",table_name="reconciliations")
    op.drop_table("reconciliations")
    op.drop_index("ix_finance_records_reference",table_name="finance_records")
    op.drop_index("ix_finance_records_tenant_id",table_name="finance_records")
    op.drop_table("finance_records")
