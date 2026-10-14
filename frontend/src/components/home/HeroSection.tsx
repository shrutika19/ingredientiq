import { ArrowDown, ArrowRight, Check, Sparkles } from 'lucide-react'
import Button from '../ui/Button'

function HeroSection() {
  return (
    <section
      className="relative isolate overflow-hidden bg-[#FAF9F6]"
      id="home"
    >
      <div className="pointer-events-none absolute -right-32 -top-36 -z-10 size-[34rem] rounded-full bg-[#e9eee7]/70 blur-3xl" />
      <div className="pointer-events-none absolute -bottom-48 left-[-8rem] -z-10 size-[28rem] rounded-full bg-[#f0e9de]/70 blur-3xl" />

      <div className="mx-auto grid max-w-7xl items-center gap-14 px-5 py-16 sm:px-8 sm:py-20 lg:grid-cols-[1fr_0.95fr] lg:gap-16 lg:px-10 lg:py-24">
        <div className="relative z-10 max-w-2xl">
          <div className="mb-7 inline-flex items-center gap-2 rounded-full border border-[#dce5dc] bg-white/70 px-4 py-2 text-xs font-semibold tracking-wide text-[#44654e]">
            <Sparkles aria-hidden="true" size={15} />
            A more thoughtful way to care for your skin
          </div>
          <h1 className="font-display text-5xl leading-[1.07] tracking-[-0.04em] text-[#252525] sm:text-6xl lg:text-[4.4rem]">
            Your Skincare Deserves{' '}
            <span className="italic text-[#668772]">a Second Look.</span>
          </h1>
          <p className="mt-6 max-w-xl text-base leading-7 text-[#6b6d68] sm:text-lg sm:leading-8">
            Discover what&apos;s really inside your skincare products.
            Understand ingredients, explore their benefits, and uncover
            potential concerns with AI-powered insights.
          </p>
          <div className="mt-8 flex flex-col gap-3 sm:flex-row">
            <Button href="#analyzer">
              Analyze Ingredients
              <ArrowRight aria-hidden="true" size={17} />
            </Button>
            <Button href="#how-it-works" variant="secondary">
              How It Works
              <ArrowDown aria-hidden="true" size={16} />
            </Button>
          </div>
          <div className="mt-8 flex flex-wrap items-center gap-x-6 gap-y-3 text-xs text-[#777a73]">
            <span className="inline-flex items-center gap-2">
              <Check aria-hidden="true" className="text-[#688772]" size={15} />
              Clear, easy-to-understand insights
            </span>
            <span className="inline-flex items-center gap-2">
              <Check aria-hidden="true" className="text-[#688772]" size={15} />
              Made for curious skin
            </span>
          </div>
        </div>

        <div className="relative mx-auto w-full max-w-[34rem] lg:max-w-none">
          <div className="absolute -left-4 top-12 z-10 hidden rounded-full border border-white/80 bg-white/90 p-3 text-[#708b73] shadow-lg shadow-[#334b3814] sm:block">
            <span className="grid size-11 place-items-center rounded-full bg-[#eef2e9]">
              <Sparkles aria-hidden="true" size={20} />
            </span>
          </div>
          <div className="absolute -right-3 bottom-14 z-10 hidden rounded-full border border-white/80 bg-white/90 p-3 text-[#708b73] shadow-lg shadow-[#334b3814] sm:block">
            <LeafDecor />
          </div>
          <div className="relative overflow-hidden rounded-[2rem] bg-[#e7e5d9] shadow-[0_30px_80px_-35px_rgba(41,75,58,0.38)]">
            <img
              alt="Minimal skincare bottles surrounded by soft natural light"
              className="h-[26rem] w-full object-cover sm:h-[33rem]"
              src="https://images.unsplash.com/photo-1608248543803-ba4f8c70ae0b?auto=format&fit=crop&w=1200&q=85"
            />
            <div className="absolute inset-0 bg-gradient-to-t from-[#1e3328]/25 via-transparent to-white/10" />
            <div className="absolute bottom-5 left-5 right-5 rounded-2xl border border-white/60 bg-white/90 p-4 shadow-lg backdrop-blur-md sm:bottom-7 sm:left-7 sm:right-7 sm:p-5">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-[10px] font-bold uppercase tracking-[0.17em] text-[#819383]">
                    Ingredient spotlight
                  </p>
                  <p className="mt-1.5 font-display text-xl text-[#294B3A]">
                    Squalane
                  </p>
                  <p className="mt-1 text-xs leading-5 text-[#777a73]">
                    A lightweight emollient that helps soften and hydrate skin.
                  </p>
                </div>
                <span className="shrink-0 rounded-full bg-[#e9f0e8] px-3 py-1.5 text-[10px] font-semibold text-[#52745a]">
                  Skin-friendly
                </span>
              </div>
            </div>
          </div>
          <div className="absolute -bottom-7 -left-2 hidden max-w-[12rem] rounded-2xl border border-white/80 bg-white/90 p-4 shadow-xl shadow-[#334b3814] backdrop-blur sm:block">
            <p className="font-display text-sm text-[#294B3A]">Know what&apos;s in it.</p>
            <p className="mt-1 text-xs leading-5 text-[#777a73]">
              Ingredient clarity, at a glance.
            </p>
          </div>
        </div>
      </div>
    </section>
  )
}

function LeafDecor() {
  return (
    <span aria-hidden="true" className="flex size-11 items-center justify-center text-[#789179]">
      <span className="text-2xl">✳</span>
    </span>
  )
}

export default HeroSection
