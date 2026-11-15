from __future__ import annotations
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4
import jwt
from jwt import PyJWKClient
from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, String, Numeric, DateTime, UniqueConstraint, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session, sessionmaker
from sqlalchemy.exc import IntegrityError

class Base(DeclarativeBase):
    pass

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL required; never use ephemeral production storage")
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False)

def get_db():
    with SessionLocal() as session:
        yield session

@dataclass(frozen=True)
class Principal:
    subject: str
    tenant: str
    scopes: frozenset[str]

bearer = HTTPBearer(auto_error=False)
def get_principal(auth: HTTPAuthorizationCredentials | None = Depends(bearer)) -> Principal:
    if auth is None:
        raise HTTPException(401, "Bearer token required")
    issuer = os.getenv("OIDC_ISSUER")
    audience = os.getenv("OIDC_AUDIENCE")
    jwks = os.getenv("OIDC_JWKS_URL")
    if not all([issuer, audience, jwks]):
        raise HTTPException(503, "OIDC issuer is not configured")
    try:
        key = PyJWKClient(jwks).get_signing_key_from_jwt(auth.credentials)
        claims = jwt.decode(auth.credentials, key.key, algorithms=["RS256"],
                            audience=audience, issuer=issuer,
                            options={"require":["sub","iss","aud","exp","iat"]})
    except Exception as error:
        raise HTTPException(401, "Invalid access token") from error
    tenant = claims.get("tenant_id")
    if not isinstance(tenant, str) or not tenant:
        raise HTTPException(403, "Tenant required")
    from app.regional_policy import enforce_residency
    enforce_residency(claims, tenant)
    scopes = claims.get("scope", "")
    return Principal(claims["sub"], tenant, frozenset(scopes.split() if isinstance(scopes, str) else []))

def require(scope: str):
    def check(p: Principal = Depends(get_principal)):
        if scope not in p.scopes:
            raise HTTPException(403, "Insufficient scope")
        return p
    return check

app = FastAPI(version="0.1.0")
from app.middleware import EnterpriseRequestMiddleware
app.add_middleware(EnterpriseRequestMiddleware)

@app.get("/healthz")
def healthz():
    return {"status":"ok"}

@app.get("/readyz")
def readyz(db: Session = Depends(get_db)):
    db.execute(select(1))
    return {"status":"ready"}

class FinanceRecord(Base):
    __tablename__="finance_records"
    id: Mapped[str] = mapped_column(String(36),primary_key=True,default=lambda:str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(100),index=True)
    source: Mapped[str] = mapped_column(String(20))
    external_id: Mapped[str] = mapped_column(String(100))
    reference: Mapped[str] = mapped_column(String(100),index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(18,2))
    currency: Mapped[str] = mapped_column(String(3))
    __table_args__=(UniqueConstraint("tenant_id","source","external_id"),)

class Reconciliation(Base):
    __tablename__="reconciliations"
    id: Mapped[str] = mapped_column(String(36),primary_key=True,default=lambda:str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(100),index=True)
    reference: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(30))
    details: Mapped[str] = mapped_column(String(300))
    __table_args__=(UniqueConstraint("tenant_id","reference"),)

class FinanceNew(BaseModel):
    source: str = Field(pattern="^(erp|bank)$")
    external_id: str = Field(min_length=1,max_length=100)
    reference: str = Field(min_length=1,max_length=100)
    amount: Decimal = Field(max_digits=18,decimal_places=2)
    currency: str = Field(default="USD",pattern=r"^[A-Z]{3}$")

@app.post("/v1/records",status_code=201)
def ingest(body:FinanceNew,p:Principal=Depends(require("finance:write")),db:Session=Depends(get_db)):
    prev=db.scalar(select(FinanceRecord).where(FinanceRecord.tenant_id==p.tenant,FinanceRecord.source==body.source,FinanceRecord.external_id==body.external_id))
    if prev:
        if (prev.reference,prev.amount,prev.currency)!=(body.reference,body.amount,body.currency):
            raise HTTPException(409,"Conflicting duplicate")
        return {"id":prev.id,"replayed":True}
    item=FinanceRecord(tenant_id=p.tenant,**body.model_dump());db.add(item)
    try:db.commit()
    except IntegrityError:db.rollback();raise HTTPException(409,"Concurrent duplicate; retry")
    db.refresh(item)
    return {"id":item.id,"replayed":False}

@app.post("/v1/reconcile/{reference}")
def reconcile(reference:str,p:Principal=Depends(require("finance:reconcile")),db:Session=Depends(get_db)):
    records=db.scalars(select(FinanceRecord).where(FinanceRecord.tenant_id==p.tenant,FinanceRecord.reference==reference)).all()
    erp=[r for r in records if r.source=="erp"];bank=[r for r in records if r.source=="bank"]
    if len(erp)!=1 or len(bank)!=1:status,detail="exception","Missing or ambiguous record"
    elif (erp[0].amount,erp[0].currency)!=(bank[0].amount,bank[0].currency):status,detail="exception","Amount or currency mismatch"
    else:status,detail="matched","Exact match"
    item=db.scalar(select(Reconciliation).where(Reconciliation.tenant_id==p.tenant,Reconciliation.reference==reference))
    if item is None:db.add(Reconciliation(tenant_id=p.tenant,reference=reference,status=status,details=detail))
    else:item.status=status;item.details=detail
    db.commit()
    return {"reference":reference,"status":status,"details":detail}

@app.get("/v1/exceptions")
def exceptions(p:Principal=Depends(require("finance:read")),db:Session=Depends(get_db)):
    return [{"reference":r.reference,"details":r.details}
            for r in db.scalars(select(Reconciliation).where(Reconciliation.tenant_id==p.tenant,Reconciliation.status=="exception"))]
