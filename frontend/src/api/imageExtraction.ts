const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'
).replace(/\/$/, '')

export interface ImageExtractionResponse {
  status: string
  ingredient_text: string
  extraction_status: string
  warnings: string[]
}

export class ImageExtractionApiError extends Error {
  readonly status: number
  readonly code?: string

  constructor(message: string, status: number, code?: string) {
    super(message)
    this.name = 'ImageExtractionApiError'
    this.status = status
    this.code = code
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

function isImageExtractionResponse(
  payload: unknown,
): payload is ImageExtractionResponse {
  return (
    isRecord(payload) &&
    typeof payload.status === 'string' &&
    typeof payload.ingredient_text === 'string' &&
    typeof payload.extraction_status === 'string' &&
    Array.isArray(payload.warnings) &&
    payload.warnings.every((warning) => typeof warning === 'string')
  )
}

function getErrorDetails(payload: unknown) {
  if (!isRecord(payload)) {
    return undefined
  }

  const detail = isRecord(payload.detail) ? payload.detail : payload
  const error = isRecord(detail.error) ? detail.error : undefined

  return {
    code:
      typeof error?.code === 'string'
        ? error.code
        : typeof detail.error === 'string'
          ? detail.error
          : undefined,
    message:
      typeof error?.message === 'string'
        ? error.message
        : typeof detail.message === 'string'
          ? detail.message
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

export async function extractIngredientsFromImage(
  file: File,
): Promise<ImageExtractionResponse> {
  const formData = new FormData()
  formData.append('file', file)

  const response = await fetch(`${API_BASE_URL}/api/v1/ingredients/extract-image`, {
    method: 'POST',
    body: formData,
  })
  const payload = await readJson(response)

  if (!response.ok) {
    const error = getErrorDetails(payload)
    throw new ImageExtractionApiError(
      error?.message ??
        `Image extraction failed (HTTP ${response.status}). Please try again.`,
      response.status,
      error?.code,
    )
  }

  if (!isImageExtractionResponse(payload)) {
    throw new ImageExtractionApiError(
      'The server returned an unexpected image extraction response.',
      response.status,
    )
  }

  return payload
}
