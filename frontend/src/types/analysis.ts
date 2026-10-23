export type AnalysisStatus =
  | 'PENDING'
  | 'PROCESSING'
  | 'COMPLETED'
  | 'FAILED'

export type ConcernLevel = 'low' | 'moderate' | 'high' | 'unknown'

export type FindingSupport = 'supported' | 'limited' | 'conflicting'

export type EvidenceCoverage = 'full' | 'partial' | 'unavailable'

export type OverallAssessment =
  | 'low_concern'
  | 'moderate_concern'
  | 'high_concern'
  | 'insufficient_data'

export interface AnalyzedIngredient {
  name: string
  function: string
  concern_level: ConcernLevel
  explanation: string
  support_status?: FindingSupport
  supporting_quote?: string | null
  evidence_ids?: string[]
}

export interface GeminiAnalysisResult {
  overall_assessment: OverallAssessment
  summary: string
  ingredients: AnalyzedIngredient[]
  cautions: string[]
  uncertainties: string[]
  evidence_status?: 'source_grounded' | 'limited'
  evidence_ids?: string[]
}

export interface AnalysisEvidenceReference {
  evidence_id: string
  source_identifier: string
  source_organization?: string | null
  document_title: string
  original_url: string
  excerpt: string
  ingredient_name: string
  location_reference?: string | null
}

export interface IngredientAnalysisResponse {
  analysis_id: string
  submission_id: string
  status: AnalysisStatus
  result: GeminiAnalysisResult | null
  evidence_references?: AnalysisEvidenceReference[] | null
  evidence_coverage?: EvidenceCoverage
  failure_code: string | null
  created_at: string
  completed_at: string | null
}

export interface AnalysisApiErrorResponse {
  error?: string
  message?: string
}
