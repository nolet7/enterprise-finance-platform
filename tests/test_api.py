import pytest
from fastapi import HTTPException, Request
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app import main as m

@pytest.fixture
def lab():
    engine=create_engine("sqlite+pysqlite://",connect_args={"check_same_thread":False},poolclass=StaticPool)
    m.Base.metadata.create_all(engine)
    factory=sessionmaker(bind=engine)
    principals={}
    def get_db():
        with factory() as s: yield s
    def get_principal(req:Request):
        token=req.headers.get("Authorization","").removeprefix("Bearer ")
        if token not in principals:raise HTTPException(401,"Unauthorized")
        return principals[token]
    m.app.dependency_overrides[m.get_db]=get_db
    m.app.dependency_overrides[m.get_principal]=get_principal
    with TestClient(m.app) as client:
        def auth(user,tenant,scopes):
            token="test-"+str(len(principals))
            principals[token]=m.Principal(user,tenant,frozenset(scopes))
            return {"Authorization":"Bearer "+token}
        yield client,auth
    m.app.dependency_overrides.clear()
    engine.dispose()

def test_health(lab):
    client,auth=lab
    assert client.get("/healthz").json()=={"status":"ok"}

def test_bearer_is_required():
    with pytest.raises(HTTPException) as e:
        m.get_principal(None)
    assert e.value.status_code==401

def test_reconciliation_and_exception(lab):
    client,auth=lab
    analyst=auth("analyst","tenant-a",["finance:write","finance:read","finance:reconcile"])
    erp={"source":"erp","external_id":"inv-1","reference":"REF-01","amount":"120.00"}
    bank={"source":"bank","external_id":"stmt-1","reference":"REF-01","amount":"120.00"}
    a=client.post("/v1/records",headers=analyst,json=erp)
    assert a.status_code==201,a.text
    assert client.post("/v1/records",headers=analyst,json=erp).json()["replayed"]
    assert client.post("/v1/records",headers=analyst,json=bank).status_code==201
    assert client.post("/v1/reconcile/REF-01",headers=analyst).json()["status"]=="matched"
    assert client.post("/v1/reconcile/MISSING",headers=analyst).json()["status"]=="exception"
    assert len(client.get("/v1/exceptions",headers=analyst).json())==1
    assert client.get("/v1/exceptions",headers=auth("other","tenant-b",["finance:read"])).json()==[]
