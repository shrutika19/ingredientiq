import type {
  AnalysisApiErrorResponse,
  IngredientAnalysisResponse,
} from '../types/analysis'

const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'
).replace(/\/$/, '')

export class AnalysisApiError extends Error {
  readonly status: number
  readonly code?: string

  constructor(
    message: string,
    status: number,
    code?: string,
  ) {
    super(message)
    this.name = 'AnalysisApiError'
    this.status = status
    this.code = code
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

function isIngredientAnalysisResponse(
  payload: unknown,
): payload is IngredientAnalysisResponse {
  return (
    isRecord(payload) &&
    typeof payload.analysis_id === 'string' &&
    typeof payload.submission_id === 'string' &&
    typeof payload.status === 'string' &&
    ['PENDING', 'PROCESSING', 'COMPLETED', 'FAILED'].includes(
      payload.status,
    ) &&
    (payload.result === null || isRecord(payload.result)) &&
    (typeof payload.failure_code === 'string' ||
      payload.failure_code === null) &&
    typeof payload.created_at === 'string' &&
    (typeof payload.completed_at === 'string' ||
      payload.completed_at === null)
  )
}

function getErrorDetails(
  payload: unknown,
): AnalysisApiErrorResponse | undefined {
  if (!isRecord(payload)) {
    return undefined
  }

  const detail = isRecord(payload.detail) ? payload.detail : payload
  return {
    error: typeof detail.error === 'string' ? detail.error : undefined,
    message:
      typeof detail.message === 'string' ? detail.message : undefined,
  }
}

async function requestAnalysis(
  url: string,
  init?: RequestInit,
): Promise<IngredientAnalysisResponse> {
  const response = await fetch(url, init)
  const payload = await readJson(response)

  if (!response.ok) {
    const error = getErrorDetails(payload)
    throw new AnalysisApiError(
      error?.message ??
        `Analysis request failed (HTTP ${response.status}). Please try again.`,
      response.status,
      error?.error,
    )
  }

  if (!isIngredientAnalysisResponse(payload)) {
    throw new AnalysisApiError(
      'The server returned an unexpected analysis response.',
      response.status,
    )
  }

  return payload
}

async function readJson(response: Response): Promise<unknown> {
  try {
    return await response.json()
  } catch {
    return null
  }
}

export function startIngredientAnalysis(
  submissionId: string,
): Promise<IngredientAnalysisResponse> {
  return requestAnalysis(
    `${API_BASE_URL}/api/v1/submissions/${encodeURIComponent(submissionId)}/analyze`,
    { method: 'POST' },
  )
}

export function getIngredientAnalysis(
  submissionId: string,
): Promise<IngredientAnalysisResponse> {
  return requestAnalysis(
    `${API_BASE_URL}/api/v1/submissions/${encodeURIComponent(submissionId)}/analysis`,
  )
}
