"""Defense-in-depth residency gate for independently deployed LSK regional stacks.

The trusted identity provider must issue the tenant_id and data_region claims.
Region values must be configured by regional platform owners. Enforcement is
mandatory in Terraform deployment but can be disabled locally for unit tests.
No shared cross-region tenant records or fallback routing is permitted.
"""
from __future__ import annotations

import json
import os

from fastapi import HTTPException


def enforce_residency(claims: dict, tenant_id: str) -> None:
    if os.getenv("LSK_ENFORCE_RESIDENCY", "false").lower() != "true":
        return

    deployed_region = os.getenv("LSK_DEPLOYMENT_REGION", "")
    raw_policy = os.getenv("LSK_TENANT_REGION_POLICY", "")
    if not deployed_region or not raw_policy:
        raise HTTPException(503, "Regional residency policy is not configured")
    try:
        policy = json.loads(raw_policy)
    except (ValueError, TypeError) as exc:
        raise HTTPException(503, "Regional residency policy is invalid") from exc
    if not isinstance(policy, dict):
        raise HTTPException(503, "Regional residency policy must map tenants to regions")
    approved = policy.get(tenant_id)
    if not isinstance(approved, list) or not approved or not all(isinstance(x, str) for x in approved):
        raise HTTPException(403, "Tenant is not assigned to this region")
    claim_region = claims.get("data_region")
    if not isinstance(claim_region, str) or not claim_region:
        raise HTTPException(403, "Signed data_region claim required")
    if deployed_region != claim_region or deployed_region not in approved:
        raise HTTPException(403, "Tenant data region mismatch")


def get_regional_status() -> dict:
    return {"enforced": os.getenv("LSK_ENFORCE_RESIDENCY", "false").lower() == "true",
            "region": os.getenv("LSK_DEPLOYMENT_REGION", "")}
