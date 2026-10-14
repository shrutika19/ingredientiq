import { ArrowRight, ClipboardList, Microscope, ScanSearch } from 'lucide-react'
import SectionHeading from '../ui/SectionHeading'

const steps = [
  {
    number: '01',
    title: 'Add Ingredients',
    description: 'Paste an ingredient list or upload a product label.',
    Icon: ClipboardList,
  },
  {
    number: '02',
    title: 'AI Analyzes',
    description: 'IngredientIQ examines ingredients, their purposes, and potential concerns.',
    Icon: Microscope,
  },
  {
    number: '03',
    title: 'Get Insights',
    description: 'Understand beneficial ingredients, potential irritants, and the overall product.',
    Icon: ScanSearch,
  },
]

function HowItWorks() {
  return (
    <section className="bg-[#FAF9F6] px-5 py-20 sm:px-8 sm:py-24 lg:px-10" id="how-it-works">
      <div className="mx-auto max-w-7xl">
        <SectionHeading
          description="A little more clarity, in three simple steps."
          eyebrow="Simple by design"
          title="A clearer routine starts here"
        />
        <div className="relative mt-14 grid gap-5 md:grid-cols-3 md:gap-6">
          <div className="absolute left-[20%] right-[20%] top-10 hidden border-t border-dashed border-[#cbd7ca] md:block" />
          {steps.map(({ number, title, description, Icon }) => (
            <article
              className="relative rounded-3xl border border-[#eeeee8] bg-white p-7 transition duration-300 hover:-translate-y-1 hover:shadow-[0_16px_35px_-25px_rgba(41,75,58,0.45)] sm:p-8"
              key={number}
            >
              <div className="relative flex items-center justify-between">
                <span className="grid size-14 place-items-center rounded-2xl bg-[#eaf0e8] text-[#52745a]">
                  <Icon aria-hidden="true" size={23} strokeWidth={1.7} />
                </span>
                <span className="font-display text-3xl text-[#d7ded5]">{number}</span>
              </div>
              <h3 className="mt-7 font-display text-2xl text-[#294B3A]">{title}</h3>
              <p className="mt-3 text-sm leading-6 text-[#777a73]">{description}</p>
              {number !== '03' && (
                <ArrowRight
                  aria-hidden="true"
                  className="absolute -right-4 top-9 z-10 hidden rounded-full border border-[#e7e9e1] bg-[#FAF9F6] p-2 text-[#829683] md:block"
                  size={32}
                />
              )}
            </article>
          ))}
        </div>
      </div>
    </section>
  )
}

export default HowItWorks
