"""The region gate refuses bad tokens/policies before business actions execute."""
import json

import pytest
from fastapi import HTTPException
from app.regional_policy import enforce_residency


@pytest.fixture
def regional_config(monkeypatch):
    monkeypatch.setenv("LSK_ENFORCE_RESIDENCY", "true")
    monkeypatch.setenv("LSK_DEPLOYMENT_REGION", "us-central1")
    monkeypatch.setenv("LSK_TENANT_REGION_POLICY",
                       json.dumps({"tenant-us": ["us-central1"], "tenant-eu": ["europe-west1"]}))


def test_correct_tenant_and_signed_region(regional_config):
    enforce_residency({"data_region": "us-central1"}, "tenant-us")


@pytest.mark.parametrize("claim,tenant", [
    ({"data_region": "europe-west1"}, "tenant-us"),
    ({"data_region": "us-central1"}, "tenant-eu"),
    ({}, "tenant-us"),
    ({"data_region": "us-central1"}, "unknown"),
])
def test_reject_cross_region_and_missing_claim(regional_config, claim, tenant):
    with pytest.raises(HTTPException) as exc:
        enforce_residency(claim, tenant)
    assert exc.value.status_code == 403


def test_fail_closed_on_invalid_configuration(regional_config, monkeypatch):
    monkeypatch.setenv("LSK_TENANT_REGION_POLICY", "not-json")
    with pytest.raises(HTTPException) as exc:
        enforce_residency({"data_region": "us-central1"}, "tenant-us")
    assert exc.value.status_code == 503


def test_disabled_only_for_local_development(monkeypatch):
    monkeypatch.setenv("LSK_ENFORCE_RESIDENCY", "false")
    enforce_residency({}, "tenant-unassigned")
