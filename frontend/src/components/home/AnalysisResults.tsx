import {
  AlertTriangle,
  CheckCircle2,
  CircleHelp,
  LoaderCircle,
  RotateCcw,
  Sparkles,
} from 'lucide-react'
import type {
  AnalysisStatus,
  IngredientAnalysisResponse,
  OverallAssessment,
} from '../../types/analysis'
import Button from '../ui/Button'

interface AnalysisResultsProps {
  analysis: IngredientAnalysisResponse | null
  errorMessage: string | null
  isLoading: boolean
  onRetry: () => void
  retryLabel?: string
}

const assessmentLabels: Record<OverallAssessment, string> = {
  low_concern: 'Lower concern',
  moderate_concern: 'Some considerations',
  high_concern: 'More considerations',
  insufficient_data: 'Insufficient data',
}

const assessmentClasses: Record<OverallAssessment, string> = {
  low_concern: 'bg-[#eaf0e8] text-[#41664a]',
  moderate_concern: 'bg-[#f8f2df] text-[#796536]',
  high_concern: 'bg-[#fbefec] text-[#8c4038]',
  insufficient_data: 'bg-[#f0f0ed] text-[#666960]',
}

function getStatusLabel(status: AnalysisStatus): string {
  return status === 'PENDING' ? 'Waiting to start' : 'Analysis in progress'
}

function getFailureMessage(failureCode: string | null): string {
  if (
    failureCode === 'GEMINI_UNAVAILABLE' ||
    failureCode === 'GEMINI_RATE_LIMIT' ||
    failureCode === 'GEMINI_TIMEOUT'
  ) {
    return 'Our analysis service is temporarily unavailable. Your ingredient list is saved. Please try again shortly.'
  }

  if (failureCode === 'GEMINI_AUTH_ERROR') {
    return 'Our analysis service is temporarily unavailable. Your ingredient list is saved; please try again later.'
  }

  return 'We could not complete this analysis. Your ingredient list is saved, so you can safely retry.'
}

function AnalysisResults({
  analysis,
  errorMessage,
  isLoading,
  onRetry,
  retryLabel = 'Retry analysis',
}: AnalysisResultsProps) {
  if (!analysis && !isLoading && !errorMessage) {
    return null
  }

  const result = analysis?.result
  const isProcessing =
    isLoading ||
    analysis?.status === 'PENDING' ||
    analysis?.status === 'PROCESSING'

  return (
    <section
      aria-live="polite"
      className="mt-7 border-t border-[#eeeee8] pt-7"
      id="analysis-results"
    >
      {isProcessing && (
        <div className="flex items-center gap-3 rounded-2xl bg-[#f4f6f1] p-5 text-sm text-[#48634c]" role="status">
          <LoaderCircle aria-hidden="true" className="shrink-0 animate-spin" size={20} />
          <div>
            <p className="font-semibold">
              {analysis ? getStatusLabel(analysis.status) : 'Analyzing ingredients…'}
            </p>
            <p className="mt-1 text-xs text-[#7b8178]">
              This can take a few moments. Please keep this page open.
            </p>
          </div>
        </div>
      )}

      {!isProcessing && errorMessage && (
        <div className="rounded-2xl border border-[#f0d8d3] bg-[#fbf2ef] p-5" role="alert">
          <div className="flex items-start gap-3">
            <AlertTriangle aria-hidden="true" className="mt-0.5 shrink-0 text-[#a14e43]" size={19} />
            <div className="min-w-0 flex-1">
              <p className="text-sm font-semibold text-[#713b34]">
                We couldn&apos;t load the analysis
              </p>
              <p className="mt-1 text-sm leading-6 text-[#875d56]">{errorMessage}</p>
              <Button
                className="mt-4 min-h-10 px-4 py-2 text-xs disabled:opacity-60"
                disabled={isLoading}
                onClick={onRetry}
                type="button"
                variant="secondary"
              >
                <RotateCcw aria-hidden="true" size={14} />
                {retryLabel}
              </Button>
            </div>
          </div>
        </div>
      )}

      {!isProcessing && analysis?.status === 'FAILED' && (
        <div className="rounded-2xl border border-[#f0d8d3] bg-[#fbf2ef] p-5" role="alert">
          <div className="flex items-start gap-3">
            <AlertTriangle aria-hidden="true" className="mt-0.5 shrink-0 text-[#a14e43]" size={19} />
            <div>
              <p className="text-sm font-semibold text-[#713b34]">Analysis couldn&apos;t be completed</p>
              <p className="mt-1 text-sm leading-6 text-[#875d56]">
                {getFailureMessage(analysis.failure_code)}
              </p>
              <Button
                className="mt-4 min-h-10 px-4 py-2 text-xs disabled:opacity-60"
                disabled={isLoading}
                onClick={onRetry}
                type="button"
                variant="secondary"
              >
                <RotateCcw aria-hidden="true" size={14} />
                Retry analysis
              </Button>
            </div>
          </div>
        </div>
      )}

      {!isProcessing && !errorMessage && analysis?.status === 'COMPLETED' && result && (
        <div>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <Sparkles aria-hidden="true" className="text-[#688772]" size={18} />
              <h3 className="font-display text-2xl text-[#294B3A]">
                Your ingredient insights
              </h3>
            </div>
            <span className="rounded-full bg-[#f2eee5] px-3 py-1.5 text-[10px] font-semibold tracking-wide text-[#85785f]">
              AI-GENERATED INFORMATION
            </span>
          </div>

          <article className="mt-5 rounded-2xl border border-[#e7e9e1] bg-[#fafbf8] p-5 sm:p-6">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h4 className="text-sm font-semibold text-[#3b433c]">Overall assessment</h4>
              <span className={`rounded-full px-3 py-1.5 text-xs font-semibold ${assessmentClasses[result.overall_assessment]}`}>
                {assessmentLabels[result.overall_assessment]}
              </span>
            </div>
            <p className="mt-3 text-sm leading-7 text-[#62685f]">{result.summary}</p>
          </article>

          <section className="mt-7">
            <h4 className="text-sm font-semibold text-[#353b35]">
              Ingredient breakdown
              <span className="ml-2 font-normal text-[#898c85]">
                ({result.ingredients.length})
              </span>
            </h4>
            <div className="mt-3 grid gap-3 md:grid-cols-2">
              {result.ingredients.map((ingredient, index) => (
                <article
                  className="rounded-2xl border border-[#eeeee8] bg-white p-4 sm:p-5"
                  key={`${ingredient.name}-${index}`}
                >
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <h5 className="font-semibold text-[#344138]">{ingredient.name}</h5>
                    <span className={`rounded-full px-2.5 py-1 text-[10px] font-semibold capitalize ${assessmentClasses[
                      ingredient.concern_level === 'low'
                        ? 'low_concern'
                        : ingredient.concern_level === 'moderate'
                          ? 'moderate_concern'
                          : ingredient.concern_level === 'high'
                            ? 'high_concern'
                            : 'insufficient_data'
                    ]}`}>
                      {ingredient.concern_level} concern
                    </span>
                  </div>
                  <p className="mt-3 text-xs font-semibold uppercase tracking-wide text-[#7d8d7d]">
                    Function
                  </p>
                  <p className="mt-1 text-sm text-[#52594f]">{ingredient.function}</p>
                  <p className="mt-3 text-sm leading-6 text-[#777a73]">
                    {ingredient.explanation}
                  </p>
                </article>
              ))}
            </div>
          </section>

          <div className="mt-7 grid gap-4 md:grid-cols-2">
            <InsightList
              emptyMessage="No specific cautions were identified in this analysis."
              icon="caution"
              items={result.cautions}
              title="Cautions"
            />
            <InsightList
              emptyMessage="No additional uncertainties were reported."
              icon="uncertainty"
              items={result.uncertainties}
              title="Uncertainties"
            />
          </div>

          <p className="mt-5 text-xs leading-5 text-[#92958d]">
            Ingredient insights are informational, not medical advice. Individual responses to skincare products can vary. No scientific safety score is provided.
          </p>
        </div>
      )}
    </section>
  )
}

interface InsightListProps {
  title: string
  items: string[]
  emptyMessage: string
  icon: 'caution' | 'uncertainty'
}

function InsightList({ title, items, emptyMessage, icon }: InsightListProps) {
  const Icon = icon === 'caution' ? AlertTriangle : CircleHelp

  return (
    <article className="rounded-2xl border border-[#eeeee8] bg-white p-4 sm:p-5">
      <h4 className="flex items-center gap-2 text-sm font-semibold text-[#39433b]">
        <Icon aria-hidden="true" className="text-[#8b8a70]" size={16} />
        {title}
      </h4>
      {items.length > 0 ? (
        <ul className="mt-3 space-y-2">
          {items.map((item, index) => (
            <li className="flex gap-2 text-sm leading-6 text-[#777a73]" key={`${item}-${index}`}>
              <CheckCircle2 aria-hidden="true" className="mt-1 shrink-0 text-[#8FAF9B]" size={14} />
              <span>{item}</span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-3 text-sm leading-6 text-[#898c85]">{emptyMessage}</p>
      )}
    </article>
  )
}

export default AnalysisResults
