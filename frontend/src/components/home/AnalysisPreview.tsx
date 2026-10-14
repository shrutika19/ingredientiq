import { ArrowUpRight, Check, FlaskConical, Sparkles } from 'lucide-react'
import SectionHeading from '../ui/SectionHeading'

const ingredients = [
  { name: 'Glycerin', role: 'Humectant · helps attract moisture', tone: 'sage' },
  { name: 'Ceramide NP', role: 'Skin-conditioning · supports the skin barrier', tone: 'sage' },
  { name: 'Fragrance', role: 'Fragrance component · may not suit every skin type', tone: 'sand' },
]

const benefits = [
  { name: 'Glycerin', description: 'A well-known humectant used to help draw moisture into the skin.' },
  { name: 'Ceramide NP', description: 'A lipid naturally found in the skin barrier.' },
]

function AnalysisPreview() {
  return (
    <section className="bg-[#FAF9F6] px-5 py-20 sm:px-8 sm:py-24 lg:px-10" id="sample-analysis">
      <div className="mx-auto max-w-7xl">
        <SectionHeading
          description="A glimpse of how ingredient insights could come together. This sample is illustrative, not a scientific safety assessment."
          eyebrow="A look inside"
          title="Ingredient clarity, at a glance"
        />

        <div className="mx-auto mt-12 max-w-5xl overflow-hidden rounded-[1.75rem] border border-[#e8e8e0] bg-white shadow-[0_24px_60px_-40px_rgba(41,75,58,0.35)]">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[#eeeee8] px-6 py-4 sm:px-8">
            <div className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.16em] text-[#65846f]">
              <Sparkles aria-hidden="true" size={15} />
              Sample analysis preview
            </div>
            <span className="rounded-full bg-[#f2eee5] px-3 py-1.5 text-[10px] font-semibold tracking-wide text-[#85785f]">
              MOCK DATA · NOT A REAL ANALYSIS
            </span>
          </div>

          <div className="grid lg:grid-cols-[0.82fr_1.18fr]">
            <div className="border-b border-[#eeeee8] bg-[#f8f8f3] p-6 sm:p-8 lg:border-b-0 lg:border-r">
              <div className="flex items-center gap-4">
                <div className="grid size-14 shrink-0 place-items-center rounded-2xl bg-[#e5ece5] text-[#54735b]">
                  <FlaskConical aria-hidden="true" size={25} strokeWidth={1.6} />
                </div>
                <div>
                  <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[#8a9388]">Sample product</p>
                  <h3 className="mt-1 font-display text-xl text-[#294B3A]">Daily Hydrating Moisturizer</h3>
                </div>
              </div>

              <div className="mt-7 rounded-2xl border border-[#e6e9df] bg-white p-5">
                <div className="flex items-center justify-between gap-3">
                  <p className="text-sm font-semibold text-[#353b35]">Overall assessment</p>
                  <span className="inline-flex items-center gap-1.5 rounded-full bg-[#eaf0e8] px-2.5 py-1 text-[10px] font-semibold text-[#52745a]">
                    <Check aria-hidden="true" size={12} />
                    Hydration-focused
                  </span>
                </div>
                <p className="mt-3 text-sm leading-6 text-[#777a73]">
                  A sample overview with familiar moisturizing ingredients and a fragrance component to note.
                </p>
                <div className="mt-5 flex items-center justify-between text-[10px] text-[#a0a39c]">
                  <span>Illustrative indicator</span>
                  <span>78% placeholder</span>
                </div>
                <div
                  aria-label="Illustrative placeholder indicator, not a scientific safety score"
                  className="mt-2 h-2 overflow-hidden rounded-full bg-[#edf0e9]"
                  role="img"
                >
                  <div className="h-full w-[78%] rounded-full bg-[#8FAF9B]" />
                </div>
                <p className="mt-3 text-[10px] leading-4 text-[#a0a39c]" id="disclaimer">
                  Percentages are illustrative placeholders, not safety scores or scientific measurements.
                </p>
              </div>
            </div>

            <div className="p-6 sm:p-8">
              <div>
                <h4 className="text-sm font-semibold text-[#353b35]">Sample ingredient breakdown</h4>
                <div className="mt-3 divide-y divide-[#f0f0eb]">
                  {ingredients.map(({ name, role, tone }) => (
                    <div className="flex items-start justify-between gap-4 py-3" key={name}>
                      <div>
                        <p className="text-sm font-medium text-[#3e453f]">{name}</p>
                        <p className="mt-1 text-xs leading-5 text-[#858980]">{role}</p>
                      </div>
                      <span
                        className={`mt-0.5 shrink-0 rounded-full px-2.5 py-1 text-[10px] font-semibold ${
                          tone === 'sage'
                            ? 'bg-[#eaf0e8] text-[#58745d]'
                            : 'bg-[#f3eee3] text-[#85785f]'
                        }`}
                      >
                        {tone === 'sage' ? 'Beneficial' : 'Potential concern'}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="mt-5 grid gap-3 sm:grid-cols-2">
                {benefits.map(({ name, description }) => (
                  <div className="rounded-2xl bg-[#f5f7f2] p-4" key={name}>
                    <div className="flex items-center gap-2 text-[#55765d]">
                      <span className="grid size-6 place-items-center rounded-full bg-white">
                        <Check aria-hidden="true" size={13} />
                      </span>
                      <p className="text-xs font-semibold">{name}</p>
                    </div>
                    <p className="mt-2 text-[11px] leading-5 text-[#777a73]">{description}</p>
                  </div>
                ))}
                <div className="rounded-2xl bg-[#f8f4ec] p-4 sm:col-span-2">
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-xs font-semibold text-[#786e59]">Potential concern · Fragrance</p>
                    <ArrowUpRight aria-hidden="true" className="text-[#a39371]" size={15} />
                  </div>
                  <p className="mt-2 text-[11px] leading-5 text-[#858071]">
                    Fragrance can be a consideration for some sensitive skin types. Individual experiences vary.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}

export default AnalysisPreview
