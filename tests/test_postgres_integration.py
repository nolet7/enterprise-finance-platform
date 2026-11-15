from uuid import uuid4
from decimal import Decimal
import os
import pytest
from sqlalchemy import create_engine,select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.main import FinanceRecord

@pytest.mark.skipif(not os.getenv("DATABASE_URL","").startswith("postgresql"),reason="PostgreSQL-only test")
def test_pg_finance_idempotency_and_tenant_isolation():
    engine=create_engine(os.environ["DATABASE_URL"])
    tenant="test-"+str(uuid4())
    with Session(engine) as session:
        record=FinanceRecord(tenant_id=tenant,source="erp",external_id="EXT-1",
                reference="INV-1",amount=Decimal("125.00"),currency="USD")
        session.add(record);session.commit()
        assert session.scalar(select(FinanceRecord).where(FinanceRecord.tenant_id=="other")) is None
        session.add(FinanceRecord(tenant_id=tenant,source="erp",external_id="EXT-1",
                reference="INV-2",amount=Decimal("125.00"),currency="USD"))
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()
