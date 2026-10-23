import {
  AlertTriangle,
  BookOpen,
  CheckCircle2,
  CircleHelp,
  ExternalLink,
  LoaderCircle,
  RotateCcw,
  ShieldAlert,
  Sparkles,
} from 'lucide-react'
import type {
  AnalysisEvidenceReference,
  AnalysisStatus,
  AnalyzedIngredient,
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

const concernLabels = {
  low: 'Lower potential hazard',
  moderate: 'Moderate potential hazard',
  high: 'Higher potential hazard',
  unknown: 'Not enough information',
} as const

function getStatusLabel(status: AnalysisStatus): string {
  return status === 'PENDING' ? 'Waiting to start' : 'Analysis in progress'
}

function getEvidenceReferences(
  analysis: IngredientAnalysisResponse,
  evidenceIds: string[] | undefined,
): AnalysisEvidenceReference[] {
  if (!evidenceIds?.length) {
    return []
  }

  const references = analysis.evidence_references ?? []
  return evidenceIds
    .map((evidenceId) =>
      references.find((reference) => reference.evidence_id === evidenceId),
    )
    .filter(
      (reference): reference is AnalysisEvidenceReference =>
        reference !== undefined,
    )
}

function getSafeSourceUrl(value: string): string | null {
  try {
    const url = new URL(value)
    return url.protocol === 'https:' || url.protocol === 'http:'
      ? url.toString()
      : null
  } catch {
    return null
  }
}

function getFindingSupportLabel(
  ingredient: AnalyzedIngredient,
  hasReferences: boolean,
): string {
  if (ingredient.support_status === 'conflicting' && hasReferences) {
    return 'Sources disagree'
  }
  if (ingredient.support_status === 'supported' && hasReferences) {
    return 'Source-supported'
  }
  if (ingredient.support_status === undefined) {
    return 'Evidence status unavailable'
  }
  return 'Limited evidence'
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
  const evidenceReferences = analysis?.evidence_references ?? []
  const summaryReferences = analysis
    ? getEvidenceReferences(analysis, result?.evidence_ids)
    : []
  const uniqueEvidenceReferences = [
    ...new Map(
      evidenceReferences.map((reference) => [
        reference.evidence_id,
        reference,
      ]),
    ).values(),
  ]
  const isProcessing =
    isLoading ||
    ((!errorMessage) &&
      (analysis?.status === 'PENDING' ||
        analysis?.status === 'PROCESSING'))

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
            <p className="mt-3 text-xs font-medium text-[#777a73]">
              {result.evidence_status === 'source_grounded' &&
              summaryReferences.length > 0
                ? 'Summary references are linked below.'
                : 'This AI-generated summary is not verified by linked sources.'}
            </p>
          </article>

          <aside className="mt-4 flex items-start gap-3 rounded-2xl border border-[#e7e9e1] bg-[#f6f7f3] p-4 text-sm leading-6 text-[#62685f]">
            <ShieldAlert
              aria-hidden="true"
              className="mt-0.5 shrink-0 text-[#77866f]"
              size={18}
            />
            <p>
              These findings describe potential ingredient-level hazards, not
              the risk of this finished product. Product-specific risk depends
              on factors such as concentration, formulation, amount, and
              frequency of use.
            </p>
          </aside>

          <section className="mt-7">
            <h4 className="text-sm font-semibold text-[#353b35]">
              Ingredient breakdown
              <span className="ml-2 font-normal text-[#898c85]">
                ({result.ingredients.length})
              </span>
            </h4>
            <div className="mt-3 grid gap-3 md:grid-cols-2">
              {result.ingredients.map((ingredient, index) => (
                <IngredientFinding
                  analysis={analysis}
                  ingredient={ingredient}
                  key={`${ingredient.name}-${index}`}
                />
              ))}
            </div>
          </section>

          <EvidenceSources
            analysis={analysis}
            references={uniqueEvidenceReferences}
          />

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

interface IngredientFindingProps {
  analysis: IngredientAnalysisResponse
  ingredient: AnalyzedIngredient
}

function IngredientFinding({
  analysis,
  ingredient,
}: IngredientFindingProps) {
  const references = getEvidenceReferences(
    analysis,
    ingredient.evidence_ids,
  )
  const verified =
    ingredient.support_status === 'supported' && references.length > 0
  const conflicting =
    ingredient.support_status === 'conflicting' && references.length > 0

  return (
    <article className="rounded-2xl border border-[#eeeee8] bg-white p-4 sm:p-5">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <h5 className="font-semibold text-[#344138]">{ingredient.name}</h5>
        <span
          className={`rounded-full px-2.5 py-1 text-[10px] font-semibold ${
            assessmentClasses[
              ingredient.concern_level === 'low'
                ? 'low_concern'
                : ingredient.concern_level === 'moderate'
                  ? 'moderate_concern'
                  : ingredient.concern_level === 'high'
                    ? 'high_concern'
                    : 'insufficient_data'
            ]
          }`}
        >
          {concernLabels[ingredient.concern_level]}
        </span>
      </div>
      <p className="mt-2 text-[11px] leading-5 text-[#858980]">
        Ingredient-level hazard indicator; not a finished-product risk rating.
      </p>
      <p className="mt-3 text-xs font-semibold uppercase tracking-wide text-[#7d8d7d]">
        Function
      </p>
      <p className="mt-1 text-sm text-[#52594f]">{ingredient.function}</p>
      <p className="mt-3 text-sm leading-6 text-[#777a73]">
        {ingredient.explanation}
      </p>
      <div className="mt-4 border-t border-[#f0f0eb] pt-3">
        <div className="flex flex-wrap items-center gap-2">
          <span
            className={`rounded-full px-2.5 py-1 text-[10px] font-semibold ${
              verified
                ? 'bg-[#eaf0e8] text-[#41664a]'
                : conflicting
                  ? 'bg-[#f8f2df] text-[#796536]'
                  : 'bg-[#f0f0ed] text-[#666960]'
            }`}
          >
            {getFindingSupportLabel(ingredient, references.length > 0)}
          </span>
          {references.map((reference) => (
            <a
              className="inline-flex items-center gap-1 text-xs font-medium text-[#486c55] underline decoration-[#b9c9bb] underline-offset-2 hover:text-[#294b3a]"
              href={`#evidence-ref-${encodeURIComponent(reference.evidence_id)}`}
              key={reference.evidence_id}
            >
              <BookOpen aria-hidden="true" size={13} />
              {reference.document_title || 'View source'}
            </a>
          ))}
        </div>

        {verified && ingredient.supporting_quote && (
          <blockquote className="mt-3 border-l-2 border-[#b9c9bb] pl-3 text-xs italic leading-5 text-[#62685f]">
            “{ingredient.supporting_quote}”
          </blockquote>
        )}

        {!verified && !conflicting && (
          <p className="mt-2 text-xs leading-5 text-[#777a73]">
            Not enough evidence was available to verify this finding. Treat it
            as uncertain, not as an established ingredient fact.
          </p>
        )}
        {conflicting && (
          <p className="mt-2 text-xs leading-5 text-[#777a73]">
            The linked references do not consistently support this finding.
          </p>
        )}
      </div>
    </article>
  )
}

interface EvidenceSourcesProps {
  analysis: IngredientAnalysisResponse
  references: AnalysisEvidenceReference[]
}

function EvidenceSources({
  analysis,
  references,
}: EvidenceSourcesProps) {
  const coverage =
    references.length > 0
      ? analysis.evidence_coverage
      : analysis.evidence_coverage === undefined
        ? undefined
        : 'unavailable'
  const coverageLabel =
    coverage === 'full'
      ? 'Full'
      : coverage === 'partial'
        ? 'Partial'
        : coverage === 'unavailable'
          ? 'Unavailable'
          : 'Not recorded'

  return (
    <section
      aria-labelledby="evidence-sources-heading"
      className="mt-7 rounded-2xl border border-[#e7e9e1] bg-[#fafbf8] p-4 sm:p-6"
      id="evidence-sources"
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <BookOpen aria-hidden="true" className="text-[#688772]" size={18} />
          <h4
            className="text-sm font-semibold text-[#353b35]"
            id="evidence-sources-heading"
          >
            Evidence &amp; Sources
          </h4>
        </div>
        <span className="rounded-full bg-[#f0f0ed] px-3 py-1.5 text-xs font-semibold text-[#666960]">
          Evidence coverage: {coverageLabel}
        </span>
      </div>

      {references.length > 0 ? (
        <ul className="mt-4 space-y-3">
          {references.map((reference) => {
            const safeUrl = getSafeSourceUrl(reference.original_url)
            return (
              <li
                className="scroll-mt-24 rounded-xl border border-[#eeeee8] bg-white p-4"
                id={`evidence-ref-${encodeURIComponent(reference.evidence_id)}`}
                key={reference.evidence_id}
              >
                <p className="text-xs font-semibold uppercase tracking-wide text-[#7d8d7d]">
                  {reference.source_organization?.trim() ||
                    'Organization not recorded'}
                </p>
                <h5 className="mt-1 text-sm font-semibold text-[#344138]">
                  {reference.document_title || 'Untitled source'}
                </h5>
                {reference.source_identifier && (
                  <p className="mt-1 text-xs text-[#858980]">
                    Source: {reference.source_identifier}
                  </p>
                )}
                {reference.ingredient_name && (
                  <p className="mt-1 text-xs text-[#777a73]">
                    Reference for {reference.ingredient_name}
                    {reference.location_reference
                      ? ` · ${reference.location_reference}`
                      : ''}
                  </p>
                )}
                <blockquote className="mt-3 border-l-2 border-[#d8e0d6] pl-3 text-sm leading-6 text-[#62685f]">
                  {reference.excerpt
                    ? `“${reference.excerpt}”`
                    : 'No excerpt was saved for this reference.'}
                </blockquote>
                {safeUrl && (
                  <a
                    className="mt-3 inline-flex items-center gap-1.5 text-sm font-medium text-[#486c55] underline decoration-[#b9c9bb] underline-offset-2 hover:text-[#294b3a]"
                    href={safeUrl}
                    rel="noopener noreferrer"
                    target="_blank"
                  >
                    Open original source
                    <ExternalLink aria-hidden="true" size={14} />
                  </a>
                )}
              </li>
            )
          })}
        </ul>
      ) : (
        <p className="mt-4 rounded-xl bg-white p-4 text-sm leading-6 text-[#777a73]">
          {coverage === undefined
            ? 'This saved analysis has no evidence metadata. Its findings cannot be verified from linked sources.'
            : 'No supporting references were saved for this analysis. Findings without linked sources should be treated as uncertain.'}
        </p>
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
