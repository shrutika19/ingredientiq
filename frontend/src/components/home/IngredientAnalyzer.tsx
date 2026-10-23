import { useCallback, useEffect, useRef, useState } from 'react'
import { ImagePlus, LoaderCircle, Sparkles } from 'lucide-react'
import {
  AnalysisApiError,
  getIngredientAnalysis,
  startIngredientAnalysis,
  waitForIngredientAnalysis,
} from '../../api/analysis'
import { SubmissionApiError, submitIngredients } from '../../api/submissions'
import type { IngredientAnalysisResponse } from '../../types/analysis'
import type { IngredientSubmissionResponse } from '../../types/submission'
import SectionHeading from '../ui/SectionHeading'
import Toast, { type ToastKind } from '../ui/Toast'
import AnalysisResults from './AnalysisResults'
import PasteIngredientsTab from './PasteIngredientsTab'
import UploadImageTab from './UploadImageTab'

function setSubmissionIdInUrl(submissionId: string) {
  const url = new URL(window.location.href)
  url.searchParams.set('submission_id', submissionId)
  window.history.replaceState({}, '', url)
}

function clearSubmissionIdFromUrl() {
  const url = new URL(window.location.href)
  url.searchParams.delete('submission_id')
  window.history.replaceState({}, '', url)
}

function getSubmissionIdFromUrl(): string | null {
  return new URLSearchParams(window.location.search).get('submission_id')
}

function getAnalysisErrorMessage(error: unknown): string {
  if (error instanceof AnalysisApiError) {
    if (
      error.code === 'GEMINI_UNAVAILABLE' ||
      error.code === 'GEMINI_RATE_LIMIT' ||
      error.code === 'GEMINI_TIMEOUT' ||
      error.status === 429 ||
      error.status === 502 ||
      error.status === 503 ||
      error.status === 504
    ) {
      return 'Our analysis service is temporarily unavailable. Your ingredient list is saved. Please try again shortly.'
    }

    if (error.code === 'GEMINI_AUTH_ERROR') {
      return 'Our analysis service is temporarily unavailable. Your ingredient list is saved; please try again later.'
    }

    if (error.status === 404) {
      return 'We could not find this submission. Submit your ingredient list again to start a new analysis.'
    }

    return error.message
  }

  return error instanceof Error
    ? `Could not reach the IngredientIQ API: ${error.message}`
    : 'Could not reach the IngredientIQ API. Please try again.'
}

function IngredientAnalyzer() {
  const [activeTab, setActiveTab] = useState<'paste' | 'upload'>('paste')
  const [ingredientText, setIngredientText] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [isRetrieving, setIsRetrieving] = useState(false)
  const submitRequestRef = useRef(false)
  const analysisRequestRef = useRef(false)
  const retrievalRequestRef = useRef(false)
  const [submission, setSubmission] =
    useState<IngredientSubmissionResponse | null>(null)
  const [submissionId, setSubmissionId] = useState<string | null>(
    getSubmissionIdFromUrl,
  )
  const [analysis, setAnalysis] =
    useState<IngredientAnalysisResponse | null>(null)
  const [analysisError, setAnalysisError] = useState<string | null>(null)
  const [toast, setToast] = useState<{
    kind: ToastKind
    message: string
  } | null>(null)
  const [analysisRetryAction, setAnalysisRetryAction] = useState<
    'analyze' | 'retrieve'
  >('analyze')

  const closeToast = useCallback(() => setToast(null), [])

  async function handleAnalyze(submissionId: string) {
    if (analysisRequestRef.current) {
      return
    }

    analysisRequestRef.current = true
    setIsAnalyzing(true)
    setAnalysis(null)
    setAnalysisError(null)
    setAnalysisRetryAction('analyze')

    try {
      const queued = await startIngredientAnalysis(submissionId)
      setAnalysisRetryAction('retrieve')
      const result = await waitForIngredientAnalysis(
        submissionId,
        queued,
        setAnalysis,
      )
      setAnalysis(result)
      setAnalysisRetryAction(result.status === 'FAILED' ? 'analyze' : 'retrieve')
    } catch (error) {
      const message = getAnalysisErrorMessage(error)
      setAnalysisError(message)
      setToast({ kind: 'error', message })
    } finally {
      analysisRequestRef.current = false
      setIsAnalyzing(false)
    }
  }

  const handleRetrieveAnalysis = useCallback(async (submissionId: string) => {
    if (retrievalRequestRef.current) {
      return
    }

    retrievalRequestRef.current = true
    setIsRetrieving(true)
    setAnalysisError(null)
    setAnalysisRetryAction('retrieve')

    try {
      const initial = await getIngredientAnalysis(submissionId)
      const result =
        initial.status === 'PENDING' || initial.status === 'PROCESSING'
          ? await waitForIngredientAnalysis(
              submissionId,
              initial,
              setAnalysis,
            )
          : initial
      setAnalysis(result)
      setAnalysisRetryAction(result.status === 'FAILED' ? 'analyze' : 'retrieve')
      if (result.status === 'PROCESSING' || result.status === 'PENDING') {
        setAnalysisError(null)
      }
    } catch (error) {
      const message = getAnalysisErrorMessage(error)
      setAnalysisError(message)
      setToast({ kind: 'error', message })
    } finally {
      retrievalRequestRef.current = false
      setIsRetrieving(false)
    }
  }, [])

  useEffect(() => {
    const submissionId = getSubmissionIdFromUrl()
    if (!submissionId) {
      return
    }

    const timeoutId = window.setTimeout(() => {
      void handleRetrieveAnalysis(submissionId)
    }, 0)
    return () => window.clearTimeout(timeoutId)
  }, [handleRetrieveAnalysis])

  function handleIngredientTextChange(value: string) {
    setIngredientText(value)
    setSubmission(null)
    setSubmissionId(null)
    setAnalysis(null)
    setAnalysisError(null)
    clearSubmissionIdFromUrl()
  }

  async function handleSubmit() {
    if (submitRequestRef.current) {
      return
    }

    const normalizedText = ingredientText.trim()
    if (normalizedText.length < 3 || normalizedText.length > 10000) {
      setSubmission(null)
      setToast({
        kind: 'error',
        message:
          normalizedText.length < 3
            ? 'Enter at least 3 characters of ingredient text.'
            : 'Ingredient text must be no longer than 10,000 characters.',
      })
      return
    }

    submitRequestRef.current = true
    setIsSubmitting(true)
    setSubmission(null)
    setSubmissionId(null)
    clearSubmissionIdFromUrl()
    setAnalysis(null)
    setAnalysisError(null)

    try {
      const result = await submitIngredients({
        ingredient_text: normalizedText,
      })
      setSubmission(result)
      setSubmissionId(result.submission_id)
      setSubmissionIdInUrl(result.submission_id)
      setToast({ kind: 'success', message: result.message })
      await handleAnalyze(result.submission_id)
    } catch (error) {
      if (error instanceof SubmissionApiError) {
        const message =
          error.status === 422 || error.code === 'VALIDATION_ERROR'
            ? 'The ingredient list is invalid. Enter between 3 and 10,000 characters and try again.'
            : error.status === 503 || error.code === 'DATABASE_UNAVAILABLE'
              ? 'IngredientIQ cannot save your submission right now. Please try again shortly.'
              : error.message
        setToast({ kind: 'error', message })
      } else {
        const message =
          error instanceof Error
            ? `Could not reach the IngredientIQ API: ${error.message}`
            : 'Could not reach the IngredientIQ API. Please try again.'
        setToast({ kind: 'error', message })
      }
    } finally {
      submitRequestRef.current = false
      setIsSubmitting(false)
    }
  }

  function handleAnalysisRetry() {
    const currentSubmissionId =
      submission?.submission_id ?? submissionId ?? getSubmissionIdFromUrl()
    if (!currentSubmissionId) {
      return
    }

    if (analysisRetryAction === 'retrieve') {
      void handleRetrieveAnalysis(currentSubmissionId)
    } else {
      void handleAnalyze(currentSubmissionId)
    }
  }

  const isBusy = isSubmitting || isAnalyzing || isRetrieving
  const displayedAnalysis = analysis
  const isAnalysisLoading = isAnalyzing || isRetrieving

  return (
    <section
      className="bg-[#f1f2ec] px-5 py-20 sm:px-8 sm:py-24 lg:px-10"
      id="analyzer"
    >
      <div className="mx-auto max-w-7xl">
        <SectionHeading
          description="Paste your ingredient list or upload a product label to discover what's inside."
          eyebrow="Your ingredient companion"
          title="Decode Your Skincare Ingredients"
        />

        <div className="mx-auto mt-12 max-w-4xl overflow-hidden rounded-[1.75rem] border border-[#e6e6dd] bg-white shadow-[0_20px_55px_-35px_rgba(41,75,58,0.28)]">
          <div
            aria-label="Analyzer options"
            className="grid grid-cols-2 border-b border-[#eeeee8] p-2 sm:p-3"
            role="tablist"
          >
            <button
              aria-controls="paste-panel"
              aria-selected={activeTab === 'paste'}
              className={`flex items-center justify-center gap-2 rounded-xl px-3 py-3.5 text-sm transition ${
                activeTab === 'paste'
                  ? 'bg-[#eaf0e8] font-semibold text-[#294B3A]'
                  : 'font-medium text-[#898c85] hover:bg-[#f7f8f5] hover:text-[#294B3A]'
              }`}
              id="paste-tab"
              onClick={() => setActiveTab('paste')}
              role="tab"
              type="button"
            >
              <span className="hidden sm:inline">
                <Sparkles aria-hidden="true" size={16} />
              </span>
              Paste Ingredients
            </button>
            <button
              aria-controls="upload-panel"
              aria-selected={activeTab === 'upload'}
              className={`flex items-center justify-center gap-2 rounded-xl px-3 py-3.5 text-sm transition ${
                activeTab === 'upload'
                  ? 'bg-[#eaf0e8] font-semibold text-[#294B3A]'
                  : 'font-medium text-[#898c85] hover:bg-[#f7f8f5] hover:text-[#294B3A]'
              }`}
              id="upload-tab"
              onClick={() => setActiveTab('upload')}
              role="tab"
              type="button"
            >
              <span className="hidden sm:inline">
                <ImagePlus aria-hidden="true" size={16} />
              </span>
              Upload Image
            </button>
          </div>

          {activeTab === 'paste' ? (
            <PasteIngredientsTab
              ingredientText={ingredientText}
              isSubmitting={isBusy}
              onIngredientTextChange={handleIngredientTextChange}
              onSubmit={handleSubmit}
            />
          ) : (
            <UploadImageTab />
          )}

          {submissionId && (
            <div className="px-6 sm:px-8 md:px-10">
              {isSubmitting && !isAnalyzing && (
                <p className="flex items-center justify-center gap-2 border-t border-[#eeeee8] py-5 text-sm text-[#62685f]" role="status">
                  <LoaderCircle aria-hidden="true" className="animate-spin" size={17} />
                  Saving your ingredient list…
                </p>
              )}
              <AnalysisResults
                analysis={displayedAnalysis}
                errorMessage={analysisError}
                isLoading={isAnalysisLoading}
                onRetry={handleAnalysisRetry}
                retryLabel={analysisRetryAction === 'retrieve' ? 'Retry loading results' : 'Retry analysis'}
              />
            </div>
          )}

          <p className="border-t border-[#eeeee8] px-6 py-4 text-center text-[11px] leading-5 text-[#92958d] sm:px-8">
            Ingredient text is submitted to the API. AI analysis is provided
            by the IngredientIQ backend; image upload is not active yet.
          </p>
        </div>
      </div>
      {toast && (
        <Toast
          duration={5000}
          kind={toast.kind}
          message={toast.message}
          onClose={closeToast}
        />
      )}
    </section>
  )
}

export default IngredientAnalyzer
