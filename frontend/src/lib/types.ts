export interface Vessel {
  vessel_id: string;
  name: string;
  imo_number?: string;
  created_at?: string;
}

export interface CrewMember {
  crew_id: string;
  vessel_id: string;
  full_name: string;
  role: string;
  date_of_birth?: string;
  blood_type?: string;
  allergies?: string[];
  medical_notes?: string;
  emergency_contact?: { name: string; phone: string; relation: string };
  is_active: boolean;
  created_at?: string;
}

export interface VitalSigns {
  hr?: number;
  bp?: string;
  temp?: number;
  spo2?: number;
  rr?: number;
}

export interface HealthEvent {
  event_id: string;
  vessel_id: string;
  crew_id: string;
  logged_by: string;
  event_time: string;
  symptoms?: string[];
  vital_signs?: VitalSigns;
  diagnosis?: string;
  treatment?: string;
  protocol_used?: string;
  ai_response?: string;
  severity: "minor" | "moderate" | "serious" | "critical";
  follow_up_required: boolean;
  synced: boolean;
  created_at?: string;
}

export interface Component {
  component_id: string;
  vessel_id: string;
  name: string;
  system: "propulsion" | "electrical" | "navigation" | "hvac" | "safety" | "hull";
  manufacturer?: string;
  model_number?: string;
  serial_number?: string;
  install_date?: string;
  location?: string;
  manual_ref?: string;
  spare_parts?: string[];
  photo_path?: string;
  notes?: string;
  is_active: boolean;
  created_at?: string;
}

export interface MaintenanceLog {
  log_id: string;
  vessel_id: string;
  component_id: string;
  logged_by: string;
  event_time: string;
  issue_description?: string;
  photo_paths?: string[];
  ai_diagnosis?: string;
  ai_guidance?: string;
  parts_used?: string[];
  action_taken?: string;
  resolved: boolean;
  severity: "advisory" | "degraded" | "critical" | "down";
  follow_up?: string;
  synced: boolean;
  created_at?: string;
}

export interface SyncStatus {
  queue_depth: number;
  last_sync?: string;
}
