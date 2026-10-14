import type {
  ApiErrorResponse,
  IngredientSubmissionRequest,
  IngredientSubmissionResponse,
} from '../types/submission'

const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'
).replace(/\/$/, '')

export class SubmissionApiError extends Error {
  readonly status: number
  readonly code?: string

  constructor(
    message: string,
    status: number,
    code?: string,
  ) {
    super(message)
    this.name = 'SubmissionApiError'
    this.status = status
    this.code = code
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

function isSubmissionResponse(
  payload: unknown,
): payload is IngredientSubmissionResponse {
  return (
    isRecord(payload) &&
    typeof payload.submission_id === 'string' &&
    typeof payload.status === 'string' &&
    typeof payload.message === 'string'
  )
}

function getApiErrorDetails(payload: unknown): ApiErrorResponse['error'] {
  if (!isRecord(payload) || !isRecord(payload.error)) {
    return undefined
  }

  return {
    code:
      typeof payload.error.code === 'string' ? payload.error.code : undefined,
    message:
      typeof payload.error.message === 'string'
        ? payload.error.message
        : undefined,
  }
}

async function readJson(response: Response): Promise<unknown> {
  try {
    return await response.json()
  } catch {
    return null
  }
}

export async function submitIngredients(
  request: IngredientSubmissionRequest,
): Promise<IngredientSubmissionResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/submissions`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  })
  const payload = await readJson(response)

  if (!response.ok) {
    const apiError = getApiErrorDetails(payload)
    throw new SubmissionApiError(
      apiError?.message ??
        `Submission failed (HTTP ${response.status}). Please try again.`,
      response.status,
      apiError?.code,
    )
  }

  if (!isSubmissionResponse(payload)) {
    throw new SubmissionApiError(
      'The server returned an unexpected response. Please try again.',
      response.status,
    )
  }

  return payload
}
