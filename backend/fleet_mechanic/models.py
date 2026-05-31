"""
Pydantic models for the Fleet Mechanic evaluation pipeline.
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from enum import Enum
import uuid


class UploadStatus(str, Enum):
    pending = "pending"
    uploaded = "uploaded"
    evaluated = "evaluated"


class EvalLabel(str, Enum):
    pass_ = "pass"
    fail = "fail"
    warning = "warning"


class PatchStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    deployed = "deployed"
    rejected = "rejected"


class PatchType(str, Enum):
    system_instruction = "system_instruction"
    few_shot_example = "few_shot_example"
    rag_addition = "rag_addition"


class SensorData(BaseModel):
    rpm: Optional[float] = None
    coolant_temp_c: Optional[float] = None
    oil_pressure_bar: Optional[float] = None
    exhaust_temp_c: Optional[float] = None
    fuel_flow_lph: Optional[float] = None
    battery_voltage: Optional[float] = None
    alternator_output_a: Optional[float] = None
    raw_readings: Dict[str, Any] = Field(default_factory=dict)


class ReasoningStep(BaseModel):
    step: int
    thought: str
    observation: Optional[str] = None
    action: Optional[str] = None


class EngineTraceCreate(BaseModel):
    model_config = {"protected_namespaces": ()}

    vessel_id: str
    component_name: str
    sensor_data: SensorData
    model_prompt: str
    model_response: str
    reasoning_steps: List[ReasoningStep] = Field(default_factory=list)
    diagnosis: str
    model_name: str = "gemma4:e2b"
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class MarinaSyncRequest(BaseModel):
    traces: List[EngineTraceCreate]


class MarinaSyncReport(BaseModel):
    sync_id: str
    traces_ingested: int
    evaluations_run: int
    patches_generated: int
    flagged_count: int
    summary: str
    trace_results: List[Dict[str, Any]]
