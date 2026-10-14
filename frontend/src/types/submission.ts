export interface IngredientSubmissionRequest {
  ingredient_text: string
}

export interface IngredientSubmissionResponse {
  submission_id: string
  status: string
  message: string
}

export interface ApiErrorResponse {
  error?: {
    code?: string
    message?: string
  }
}

export type SubmissionErrorType = 'validation' | 'server' | 'network'
