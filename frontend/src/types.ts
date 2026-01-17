export interface Biomarker {
  name: string
  value: number
  unit: string
  normal_range_min?: number
  normal_range_max?: number
  status: 'normal' | 'high' | 'low' | 'critical'
  interpretation?: string
}

export interface SpecialistResult {
  name: string
  specialty: string
  location: string
  distance?: string
  rating?: number
  url?: string
}

export interface TriageState {
  session_id: string
  raw_text: string
  redacted_text: string
  lab_interpreted: boolean
  biomarkers: Record<string, Biomarker>
  interpretation_summary?: string
  specialist_needed: boolean
  specialist_condition?: string
  specialist_type?: string
  patient_zip?: string
  specialist_search_approved: boolean
  specialist_results: SpecialistResult[]
  safety_approved: boolean
  medical_disclaimer?: string
  fhir_observation_id?: string
  fhir_patient_id?: string
  created_at: string
  updated_at: string
}
