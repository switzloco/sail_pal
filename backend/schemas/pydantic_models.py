from __future__ import annotations
import json
from datetime import datetime, date
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, field_validator


# ── Vessel ──────────────────────────────────────────────────────────────────

class VesselRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    vessel_id: str
    name: str
    imo_number: Optional[str] = None
    created_at: Optional[datetime] = None


class VesselCreate(BaseModel):
    name: str
    imo_number: Optional[str] = None


# ── Crew ─────────────────────────────────────────────────────────────────────

class CrewMemberRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    crew_id: str
    vessel_id: str
    full_name: str
    role: str
    date_of_birth: Optional[date] = None
    blood_type: Optional[str] = None
    allergies: Optional[List[str]] = None
    medical_notes: Optional[str] = None
    emergency_contact: Optional[Dict[str, str]] = None
    is_active: bool = True
    created_at: Optional[datetime] = None

    @field_validator("allergies", mode="before")
    @classmethod
    def parse_allergies(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return []
        return v

    @field_validator("emergency_contact", mode="before")
    @classmethod
    def parse_emergency_contact(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return {}
        return v


class CrewMemberCreate(BaseModel):
    vessel_id: str
    full_name: str
    role: str
    date_of_birth: Optional[date] = None
    blood_type: Optional[str] = None
    allergies: Optional[List[str]] = None
    medical_notes: Optional[str] = None
    emergency_contact: Optional[Dict[str, str]] = None


class CrewMemberUpdate(BaseModel):
    full_name: Optional[str] = None
    role: Optional[str] = None
    blood_type: Optional[str] = None
    allergies: Optional[List[str]] = None
    medical_notes: Optional[str] = None
    emergency_contact: Optional[Dict[str, str]] = None
    is_active: Optional[bool] = None


# ── Health Events ────────────────────────────────────────────────────────────

class VitalSigns(BaseModel):
    hr: Optional[int] = None       # heart rate bpm
    bp: Optional[str] = None       # e.g. "120/80"
    temp: Optional[float] = None   # celsius
    spo2: Optional[int] = None     # % oxygen saturation
    rr: Optional[int] = None       # respiratory rate


class HealthEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    event_id: str
    vessel_id: str
    crew_id: str
    logged_by: str
    event_time: datetime
    symptoms: Optional[List[str]] = None
    vital_signs: Optional[Dict[str, Any]] = None
    diagnosis: Optional[str] = None
    treatment: Optional[str] = None
    protocol_used: Optional[str] = None
    ai_response: Optional[str] = None
    severity: str
    follow_up_required: bool = False
    synced: bool = False
    created_at: Optional[datetime] = None

    @field_validator("symptoms", mode="before")
    @classmethod
    def parse_symptoms(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return []
        return v

    @field_validator("vital_signs", mode="before")
    @classmethod
    def parse_vital_signs(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return {}
        return v


class HealthEventCreate(BaseModel):
    vessel_id: str
    crew_id: str
    logged_by: str
    event_time: Optional[datetime] = None
    symptoms: Optional[List[str]] = None
    vital_signs: Optional[VitalSigns] = None
    diagnosis: Optional[str] = None
    treatment: Optional[str] = None
    protocol_used: Optional[str] = None
    severity: str
    follow_up_required: bool = False


# ── Components ───────────────────────────────────────────────────────────────

class ComponentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    component_id: str
    vessel_id: str
    name: str
    system: str
    manufacturer: Optional[str] = None
    model_number: Optional[str] = None
    serial_number: Optional[str] = None
    install_date: Optional[date] = None
    location: Optional[str] = None
    manual_ref: Optional[str] = None
    spare_parts: Optional[List[str]] = None
    photo_path: Optional[str] = None
    notes: Optional[str] = None
    is_active: bool = True
    created_at: Optional[datetime] = None

    @field_validator("spare_parts", mode="before")
    @classmethod
    def parse_spare_parts(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return []
        return v


class ComponentCreate(BaseModel):
    vessel_id: str
    name: str
    system: str
    manufacturer: Optional[str] = None
    model_number: Optional[str] = None
    serial_number: Optional[str] = None
    install_date: Optional[date] = None
    location: Optional[str] = None
    manual_ref: Optional[str] = None
    spare_parts: Optional[List[str]] = None
    notes: Optional[str] = None


class ComponentUpdate(BaseModel):
    name: Optional[str] = None
    manufacturer: Optional[str] = None
    location: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


# ── Maintenance Logs ─────────────────────────────────────────────────────────

class MaintenanceLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    log_id: str
    vessel_id: str
    component_id: str
    logged_by: str
    event_time: datetime
    issue_description: Optional[str] = None
    photo_paths: Optional[List[str]] = None
    ai_diagnosis: Optional[str] = None
    ai_guidance: Optional[str] = None
    parts_used: Optional[List[str]] = None
    action_taken: Optional[str] = None
    resolved: bool = False
    severity: str
    follow_up: Optional[str] = None
    synced: bool = False
    created_at: Optional[datetime] = None

    @field_validator("photo_paths", "parts_used", mode="before")
    @classmethod
    def parse_json_list(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return []
        return v


class MaintenanceLogCreate(BaseModel):
    vessel_id: str
    component_id: str
    logged_by: str
    event_time: Optional[datetime] = None
    issue_description: Optional[str] = None
    severity: str
    follow_up: Optional[str] = None


# ── Sync Queue ───────────────────────────────────────────────────────────────

class SyncQueueRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    queue_id: str
    table_name: str
    record_id: str
    operation: str
    payload: Optional[str] = None
    attempted_at: Optional[datetime] = None
    synced_at: Optional[datetime] = None
    error: Optional[str] = None


class SyncStatusRead(BaseModel):
    queue_depth: int
    last_sync: Optional[datetime] = None


# ── AI ───────────────────────────────────────────────────────────────────────

class MedicalQueryRequest(BaseModel):
    crew_id: str
    symptoms: List[str]
    vitals: Optional[Dict[str, Any]] = None
    severity: str


class ComponentAnalysisRequest(BaseModel):
    component_id: str
    issue_description: str
    severity: str
