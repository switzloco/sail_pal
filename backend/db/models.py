import uuid
from datetime import datetime
from sqlalchemy import (
    Boolean, CheckConstraint, Column, DateTime, Date,
    Float, ForeignKey, String, Text
)
from sqlalchemy.orm import relationship
from backend.db.database import Base


def _uuid():
    return str(uuid.uuid4())


class Vessel(Base):
    __tablename__ = "vessels"

    vessel_id = Column(String, primary_key=True, default=_uuid)
    name = Column(String, nullable=False)
    imo_number = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    crew_members = relationship("CrewMember", back_populates="vessel")
    components = relationship("Component", back_populates="vessel")
    health_events = relationship("HealthEvent", back_populates="vessel")
    maintenance_logs = relationship("MaintenanceLog", back_populates="vessel")


class CrewMember(Base):
    __tablename__ = "crew_members"

    crew_id = Column(String, primary_key=True, default=_uuid)
    vessel_id = Column(String, ForeignKey("vessels.vessel_id"), nullable=False)
    full_name = Column(String, nullable=False)
    role = Column(String, nullable=False)
    date_of_birth = Column(Date)
    blood_type = Column(String)
    allergies = Column(Text)        # JSON array
    medical_notes = Column(Text)
    emergency_contact = Column(Text)  # JSON object
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    vessel = relationship("Vessel", back_populates="crew_members")
    health_events = relationship("HealthEvent", foreign_keys="HealthEvent.crew_id", back_populates="crew_member")
    logged_events = relationship("HealthEvent", foreign_keys="HealthEvent.logged_by", back_populates="logged_by_crew")
    logged_maintenance = relationship("MaintenanceLog", foreign_keys="MaintenanceLog.logged_by", back_populates="logged_by_crew")


class HealthEvent(Base):
    __tablename__ = "health_events"
    __table_args__ = (
        CheckConstraint("severity IN ('minor','moderate','serious','critical')", name="ck_health_severity"),
    )

    event_id = Column(String, primary_key=True, default=_uuid)
    vessel_id = Column(String, ForeignKey("vessels.vessel_id"), nullable=False)
    crew_id = Column(String, ForeignKey("crew_members.crew_id"), nullable=False)
    logged_by = Column(String, ForeignKey("crew_members.crew_id"), nullable=False)
    event_time = Column(DateTime, nullable=False, default=datetime.utcnow)
    symptoms = Column(Text)         # JSON array
    vital_signs = Column(Text)      # JSON: {hr, bp, temp, spo2, rr}
    diagnosis = Column(Text)
    treatment = Column(Text)
    protocol_used = Column(String)
    ai_response = Column(Text)
    severity = Column(String, nullable=False)
    follow_up_required = Column(Boolean, default=False)
    photo_paths = Column(Text)      # JSON array
    synced = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    vessel = relationship("Vessel", back_populates="health_events")
    crew_member = relationship("CrewMember", foreign_keys=[crew_id], back_populates="health_events")
    logged_by_crew = relationship("CrewMember", foreign_keys=[logged_by], back_populates="logged_events")


class Component(Base):
    __tablename__ = "components"
    __table_args__ = (
        CheckConstraint(
            "system IN ('propulsion','electrical','navigation','hvac','safety','hull')",
            name="ck_component_system",
        ),
    )

    component_id = Column(String, primary_key=True, default=_uuid)
    vessel_id = Column(String, ForeignKey("vessels.vessel_id"), nullable=False)
    name = Column(String, nullable=False)
    system = Column(String, nullable=False)
    manufacturer = Column(String)
    model_number = Column(String)
    serial_number = Column(String)
    install_date = Column(Date)
    location = Column(String)
    manual_ref = Column(String)
    spare_parts = Column(Text)    # JSON array
    photo_path = Column(String)
    notes = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    vessel = relationship("Vessel", back_populates="components")
    maintenance_logs = relationship("MaintenanceLog", back_populates="component")


class MaintenanceLog(Base):
    __tablename__ = "maintenance_logs"
    __table_args__ = (
        CheckConstraint(
            "severity IN ('advisory','degraded','critical','down')",
            name="ck_maintenance_severity",
        ),
    )

    log_id = Column(String, primary_key=True, default=_uuid)
    vessel_id = Column(String, ForeignKey("vessels.vessel_id"), nullable=False)
    component_id = Column(String, ForeignKey("components.component_id"), nullable=False)
    logged_by = Column(String, ForeignKey("crew_members.crew_id"), nullable=False)
    event_time = Column(DateTime, nullable=False, default=datetime.utcnow)
    issue_description = Column(Text)
    photo_paths = Column(Text)      # JSON array
    ai_diagnosis = Column(Text)
    ai_guidance = Column(Text)
    parts_used = Column(Text)       # JSON array
    action_taken = Column(Text)
    resolved = Column(Boolean, default=False)
    severity = Column(String, nullable=False)
    follow_up = Column(Text)
    synced = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    vessel = relationship("Vessel", back_populates="maintenance_logs")
    component = relationship("Component", back_populates="maintenance_logs")
    logged_by_crew = relationship("CrewMember", foreign_keys=[logged_by], back_populates="logged_maintenance")


class EngineTrace(Base):
    """Offline Gemma inference trace recorded on the vessel's edge device."""
    __tablename__ = "engine_traces"

    id = Column(String, primary_key=True, default=_uuid)
    vessel_id = Column(String, nullable=False)
    component_name = Column(String, nullable=False)
    sensor_data_json = Column(Text, nullable=False)
    model_prompt = Column(Text, nullable=False)
    model_response = Column(Text, nullable=False)
    reasoning_steps_json = Column(Text, default="[]")
    diagnosis = Column(Text, nullable=False)
    model_name = Column(String, default="gemma4:e2b")
    recorded_at = Column(DateTime, nullable=False)
    upload_status = Column(String, default="pending")
    phoenix_trace_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    evaluations = relationship("FleetEvaluation", back_populates="trace", cascade="all, delete-orphan")
    patches = relationship("PromptPatch", back_populates="trace", cascade="all, delete-orphan")


class FleetEvaluation(Base):
    """Gemini evaluation result for an offline engine trace."""
    __tablename__ = "fleet_evaluations"

    id = Column(String, primary_key=True, default=_uuid)
    trace_id = Column(String, ForeignKey("engine_traces.id"), nullable=False)
    evaluation_type = Column(String, nullable=False)
    score = Column(Float, nullable=False)
    label = Column(String, nullable=False)
    explanation = Column(Text, default="")
    evaluator = Column(String, default="gemini-fleet-mechanic")
    flagged = Column(Boolean, default=False)
    evaluated_at = Column(DateTime, default=datetime.utcnow)

    trace = relationship("EngineTrace", back_populates="evaluations")


class PromptPatch(Base):
    """Prompt patch drafted by the Fleet Mechanic agent to fix a bad inference."""
    __tablename__ = "prompt_patches"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','approved','deployed','rejected')",
            name="ck_patch_status",
        ),
    )

    id = Column(String, primary_key=True, default=_uuid)
    trace_id = Column(String, ForeignKey("engine_traces.id"), nullable=False)
    evaluation_id = Column(String, ForeignKey("fleet_evaluations.id"), nullable=True)
    patch_type = Column(String, nullable=False)
    original_prompt_section = Column(Text, default="")
    patched_prompt_section = Column(Text, nullable=False)
    rationale = Column(Text, default="")
    agent_reasoning = Column(Text, default="")
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)

    trace = relationship("EngineTrace", back_populates="patches")


class SyncQueue(Base):
    __tablename__ = "sync_queue"
    __table_args__ = (
        CheckConstraint(
            "operation IN ('insert','update','delete')",
            name="ck_sync_operation",
        ),
    )

    queue_id = Column(String, primary_key=True, default=_uuid)
    table_name = Column(String, nullable=False)
    record_id = Column(String, nullable=False)
    operation = Column(String, nullable=False)
    payload = Column(Text)          # JSON
    attempted_at = Column(DateTime)
    synced_at = Column(DateTime)
    error = Column(Text)
