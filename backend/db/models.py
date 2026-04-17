import uuid
from datetime import datetime
from sqlalchemy import (
    Boolean, CheckConstraint, Column, DateTime, Date,
    ForeignKey, String, Text
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
