export type AnalysisStatus =
  | 'PENDING'
  | 'PROCESSING'
  | 'COMPLETED'
  | 'FAILED'

export type ConcernLevel = 'low' | 'moderate' | 'high' | 'unknown'

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
  supporting_quote: string | null
}

export interface GeminiAnalysisResult {
  overall_assessment: OverallAssessment
  summary: string
  ingredients: AnalyzedIngredient[]
  cautions: string[]
  uncertainties: string[]
}

export interface IngredientAnalysisResponse {
  analysis_id: string
  submission_id: string
  status: AnalysisStatus
  result: GeminiAnalysisResult | null
  failure_code: string | null
  created_at: string
  completed_at: string | null
}

export interface AnalysisApiErrorResponse {
  error?: string
  message?: string
}
