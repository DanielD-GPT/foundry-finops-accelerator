import gzip
import json
import os

import pytest

import function_app


@pytest.fixture(autouse=True)
def environment(monkeypatch):
    monkeypatch.setenv(
        "FOUNDRY_RESOURCE_ID",
        "/subscriptions/sub/resourceGroups/rg/providers/Microsoft.CognitiveServices/accounts/ai",
    )
    monkeypatch.setenv("AZURE_SUBSCRIPTION_ID", "sub")
    monkeypatch.setenv("FOUNDRY_RESOURCE_GROUP", "rg")


def test_parse_cost_rows_filters_and_aggregates():
    content = b"""Date,ResourceId,ResourceName,ServiceName,MeterName,PricingModel,BillingCurrency,CostInBillingCurrency,Tags
2026-01-01,/subscriptions/sub/resourceGroups/rg/providers/Microsoft.CognitiveServices/accounts/ai,ai,Azure AI services,Input Tokens,OnDemand,USD,1.25,""team=one""
2026-01-01,/subscriptions/sub/resourceGroups/rg/providers/Microsoft.CognitiveServices/accounts/ai,ai,Azure AI services,Input Tokens,OnDemand,USD,0.75,""team=one""
2026-01-01,/subscriptions/sub/resourceGroups/rg/providers/Microsoft.Storage/storageAccounts/other,other,Storage,Data,OnDemand,USD,99.00,
"""
    rows = function_app._parse_cost_rows(content, "exports/cost.csv")
    assert len(rows) == 1
    assert rows[0]["ActualCost"] == 2.0
    assert rows[0]["MeterName"] == "Input Tokens"
    assert rows[0]["SourceBlob"] == "exports/cost.csv"


def test_parse_gzip_and_header_variants():
    content = b"""Usage date,Resource ID,Resource name,ConsumedService,Meter,Pricing model,Currency,PreTaxCost
2026-01-02,/subscriptions/sub/resourceGroups/rg/providers/Microsoft.CognitiveServices/accounts/ai,ai,Microsoft.CognitiveServices,Output Tokens,OnDemand,USD,3.5
"""
    rows = function_app._parse_cost_rows(gzip.compress(content), "exports/cost.csv.gz")
    assert rows[0]["ActualCost"] == 3.5
    assert rows[0]["UsageDate"] == "2026-01-02"


def test_invalid_cost_is_skipped(caplog):
    content = b"""Date,ResourceId,ServiceName,Cost
2026-01-01,/subscriptions/sub/resourceGroups/rg/providers/Microsoft.CognitiveServices/accounts/ai,Azure AI services,not-a-number
"""
    assert function_app._parse_cost_rows(content, "exports/cost.csv") == []
    assert "invalid cost value" in caplog.text


class _Download:
    def __init__(self, payload):
        self.payload = payload

    def readall(self):
        return self.payload


class _Blob:
    def __init__(self, payload=b"", status_code=None):
        self.payload = payload
        self.status_code = status_code
        self.uploaded = None

    def download_blob(self):
        if self.status_code:
            error = RuntimeError("download failed")
            error.status_code = self.status_code
            raise error
        return _Download(self.payload)

    def upload_blob(self, payload, overwrite):
        self.uploaded = (payload, overwrite)


class _Container:
    def __init__(self, blob):
        self.blob = blob

    def get_blob_client(self, name):
        assert name == "state/processed.json"
        return self.blob


def test_state_round_trip():
    blob = _Blob(json.dumps({"processed": ["b.csv", "a.csv"]}).encode())
    assert function_app._load_state(_Container(blob)) == {"a.csv", "b.csv"}
    function_app._save_state(_Container(blob), {"b.csv", "a.csv"})
    assert json.loads(blob.uploaded[0]) == {"processed": ["a.csv", "b.csv"]}
    assert blob.uploaded[1] is True


def test_only_404_is_treated_as_empty_state():
    assert function_app._load_state(_Container(_Blob(status_code=404))) == set()
    with pytest.raises(RuntimeError, match="download failed"):
        function_app._load_state(_Container(_Blob(status_code=500)))
