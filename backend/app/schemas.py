import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ApiKeyResponse(BaseModel):
    source: str
    has_key: bool
    has_secret: bool

    model_config = {"from_attributes": True}


class ApiKeySet(BaseModel):
    api_key: str
    api_secret: str | None = None


class WordlistResponse(BaseModel):
    id: int
    name: str
    entry_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


class ScanCreate(BaseModel):
    name: str | None = None
    domains: list[str]
    sources: list[str]
    options: dict[str, Any] = {}


class ScanResponse(BaseModel):
    id: uuid.UUID
    name: str | None
    domains: list[str]
    status: str
    sources: list[str]
    options: dict[str, Any]
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    error: str | None

    model_config = {"from_attributes": True}


class ScanListResponse(BaseModel):
    items: list[ScanResponse]
    total: int


class SubdomainResponse(BaseModel):
    id: int
    scan_id: uuid.UUID
    domain: str | None
    fqdn: str
    ip_addresses: list[str] | None
    sources: list[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class SubdomainListResponse(BaseModel):
    items: list[SubdomainResponse]
    total: int


class SourceStatus(BaseModel):
    name: str
    display_name: str
    requires_key: bool
    enabled: bool


class DnsCheckCreate(BaseModel):
    fqdns: list[str]
    scan_id: uuid.UUID | None = None
