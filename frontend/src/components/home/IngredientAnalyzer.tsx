import { useRef, useState } from 'react'
import { ImagePlus, Sparkles } from 'lucide-react'
import { SubmissionApiError, submitIngredients } from '../../api/submissions'
import type {
  IngredientSubmissionResponse,
  SubmissionErrorType,
} from '../../types/submission'
import SectionHeading from '../ui/SectionHeading'
import PasteIngredientsTab from './PasteIngredientsTab'
import UploadImageTab from './UploadImageTab'

function IngredientAnalyzer() {
  const [activeTab, setActiveTab] = useState<'paste' | 'upload'>('paste')
  const [ingredientText, setIngredientText] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const isSubmittingRef = useRef(false)
  const [submission, setSubmission] =
    useState<IngredientSubmissionResponse | null>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [errorType, setErrorType] = useState<SubmissionErrorType | null>(null)

  function handleIngredientTextChange(value: string) {
    setIngredientText(value)
    setSubmission(null)
    setErrorMessage(null)
    setErrorType(null)
  }

  async function handleSubmit() {
    if (isSubmittingRef.current) {
      return
    }

    const normalizedText = ingredientText.trim()
    if (normalizedText.length < 3 || normalizedText.length > 10000) {
      setSubmission(null)
      setErrorType('validation')
      setErrorMessage(
        normalizedText.length < 3
          ? 'Enter at least 3 characters of ingredient text.'
          : 'Ingredient text must be no longer than 10,000 characters.',
      )
      return
    }

    isSubmittingRef.current = true
    setIsSubmitting(true)
    setSubmission(null)
    setErrorMessage(null)
    setErrorType(null)

    try {
      const result = await submitIngredients({
        ingredient_text: normalizedText,
      })
      setSubmission(result)
    } catch (error) {
      if (error instanceof SubmissionApiError) {
        if (error.status === 422 || error.code === 'VALIDATION_ERROR') {
          setErrorType('validation')
          setErrorMessage(
            'The ingredient list is invalid. Enter between 3 and 10,000 characters and try again.',
          )
        } else if (
          error.status === 503 ||
          error.code === 'DATABASE_UNAVAILABLE'
        ) {
          setErrorType('server')
          setErrorMessage(
            'IngredientIQ cannot save your submission right now. Please try again shortly.',
          )
        } else {
          setErrorType('server')
          setErrorMessage(
            error.status >= 500 || error.code === 'INTERNAL_SERVER_ERROR'
              ? 'The server could not process your submission. Please try again later.'
              : error.message,
          )
        }
      } else {
        setErrorType('network')
        setErrorMessage(
          error instanceof Error
            ? `Could not reach the IngredientIQ API: ${error.message}`
            : 'Could not reach the IngredientIQ API. Please try again.',
        )
      }
    } finally {
      isSubmittingRef.current = false
      setIsSubmitting(false)
    }
  }

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
              errorMessage={errorMessage}
              errorType={errorType}
              ingredientText={ingredientText}
              isSubmitting={isSubmitting}
              onIngredientTextChange={handleIngredientTextChange}
              onSubmit={handleSubmit}
              submission={submission}
            />
          ) : (
            <UploadImageTab />
          )}

          <p className="border-t border-[#eeeee8] px-6 py-4 text-center text-[11px] leading-5 text-[#92958d] sm:px-8">
            Ingredient text is submitted to the API. AI analysis and image
            upload are not active yet.
          </p>
        </div>
      </div>
    </section>
  )
}

export default IngredientAnalyzer
