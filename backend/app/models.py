from pydantic import BaseModel


class DeviceOut(BaseModel):
    ip: str
    mac_masked: str | None = None
    vendor: str | None = None
    hostname: str | None = None
    device_type: str | None = None


class FindingOut(BaseModel):
    ip: str
    port: int | None = None
    finding_code: str
    severity: str


class ScanResult(BaseModel):
    scan_id: int
    score: float | None = None
    devices: list[DeviceOut] = []
    findings: list[FindingOut] = []


class ScanHistoryItem(BaseModel):
    id: int
    filename: str
    timestamp: str
    network_score: float | None = None


class DiffResult(BaseModel):
    old_scan_id: int
    new_scan_id: int
    old_score: float | None = None
    new_score: float | None = None
    resolved_findings: list[dict] = []
    new_findings: list[dict] = []
    devices_added: list[str] = []
    devices_removed: list[str] = []


class ScanRequest(BaseModel):
    target: str
    confirm: bool = False


class NetworkInfo(BaseModel):
    interface: str | None = None
    gateway: str | None = None
    ip: str | None = None
    subnet: str | None = None
    error: str | None = None


class DeleteResponse(BaseModel):
    deleted: int
    message: str
