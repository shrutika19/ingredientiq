import { ArrowRight, Leaf } from 'lucide-react'
import Button from '../ui/Button'

function CTASection() {
  return (
    <section className="px-5 pb-20 sm:px-8 sm:pb-24 lg:px-10">
      <div className="relative mx-auto max-w-7xl overflow-hidden rounded-[2rem] bg-[#294B3A] px-6 py-14 text-center sm:px-12 sm:py-16">
        <div className="pointer-events-none absolute -right-20 -top-40 size-96 rounded-full border border-white/10" />
        <div className="pointer-events-none absolute -right-8 -top-28 size-72 rounded-full border border-white/10" />
        <div className="pointer-events-none absolute -bottom-44 -left-20 size-80 rounded-full bg-white/[0.04] blur-2xl" />
        <span className="relative mx-auto grid size-12 place-items-center rounded-full bg-white/10 text-[#d4e1d1]">
          <Leaf aria-hidden="true" size={21} />
        </span>
        <h2 className="relative mx-auto mt-6 max-w-3xl font-display text-3xl leading-tight text-white sm:text-4xl lg:text-5xl">
          Know Your Ingredients. Choose With Confidence.
        </h2>
        <p className="relative mx-auto mt-4 max-w-xl text-sm leading-6 text-white/70 sm:text-base">
          Make smarter skincare decisions with clear, understandable ingredient insights.
        </p>
        <Button className="relative mt-8" href="#analyzer" variant="light">
          Analyze Your Product
          <ArrowRight aria-hidden="true" size={17} />
        </Button>
      </div>
    </section>
  )
}

export default CTASection
