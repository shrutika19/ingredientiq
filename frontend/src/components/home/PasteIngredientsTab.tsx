import { Sparkles } from 'lucide-react'
import type {
  IngredientSubmissionResponse,
  SubmissionErrorType,
} from '../../types/submission'
import Button from '../ui/Button'

interface PasteIngredientsTabProps {
  ingredientText: string
  isSubmitting: boolean
  submission: IngredientSubmissionResponse | null
  errorMessage: string | null
  errorType: SubmissionErrorType | null
  onIngredientTextChange: (value: string) => void
  onSubmit: () => void
}

function PasteIngredientsTab({
  ingredientText,
  isSubmitting,
  submission,
  errorMessage,
  errorType,
  onIngredientTextChange,
  onSubmit,
}: PasteIngredientsTabProps) {
  return (
    <div
      aria-labelledby="paste-tab"
      className="p-6 sm:p-8 md:p-10"
      id="paste-panel"
      role="tabpanel"
    >
      <form
        aria-busy={isSubmitting}
        onSubmit={(event) => {
          event.preventDefault()
          onSubmit()
        }}
      >
        <label
          className="block text-sm font-semibold text-[#343a34]"
          htmlFor="ingredients"
        >
          Your ingredient list
        </label>
        <p className="mt-1 text-xs text-[#898c85]">
          Find the full list on your product packaging.
        </p>
        <textarea
          className="mt-5 min-h-48 w-full resize-y rounded-2xl border border-[#e5e7e0] bg-[#fcfcfa] p-4 text-sm leading-6 text-[#41463f] outline-none placeholder:text-[#a3a69f] focus:border-[#8FAF9B] focus:ring-4 focus:ring-[#8FAF9B]/15"
          id="ingredients"
          maxLength={10000}
          onChange={(event) => onIngredientTextChange(event.target.value)}
          placeholder="Paste your skincare ingredients here..."
          value={ingredientText}
        />
        <Button
          className="mt-5 w-full disabled:cursor-not-allowed disabled:opacity-60"
          disabled={isSubmitting}
          type="submit"
        >
          <Sparkles aria-hidden="true" size={16} />
          {isSubmitting ? 'Submitting...' : 'Analyze Ingredients'}
        </Button>
        {isSubmitting && (
          <p className="mt-4 text-center text-sm text-[#6b6d68]" role="status">
            Submitting your ingredient list…
          </p>
        )}
        {submission && (
          <p
            className="mt-4 rounded-xl bg-[#eaf0e8] p-3 text-sm text-[#294B3A]"
            role="status"
          >
            {submission.message} Reference: {submission.submission_id}
          </p>
        )}
        {errorMessage && (
          <p
            className={`mt-4 rounded-xl p-3 text-sm ${
              errorType === 'validation'
                ? 'bg-[#f8f4ec] text-[#786e59]'
                : 'bg-[#fbefec] text-[#8c4038]'
            }`}
            role="alert"
          >
            {errorMessage}
          </p>
        )}
      </form>
    </div>
  )
}

export default PasteIngredientsTab
