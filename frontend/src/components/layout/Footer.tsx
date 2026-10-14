import { Leaf } from 'lucide-react'

function Footer() {
  return (
    <footer className="bg-[#203d2f] text-white">
      <div className="mx-auto grid max-w-7xl gap-10 px-5 py-12 sm:px-8 md:grid-cols-[1fr_auto] md:items-center lg:px-10">
        <div className="max-w-sm">
          <a
            aria-label="IngredientIQ home"
            className="inline-flex items-center gap-2.5"
            href="#home"
          >
            <span className="grid size-9 place-items-center rounded-full bg-white/10 text-[#c6d6c8]">
              <Leaf aria-hidden="true" size={18} />
            </span>
            <span className="font-display text-xl font-semibold">
              Ingredient<span className="text-[#a9c3ac]">IQ</span>
            </span>
          </a>
          <p className="mt-4 text-sm leading-6 text-white/65">
            A clearer look at what goes into your skincare, so you can choose
            with a little more confidence.
          </p>
        </div>

        <nav aria-label="Footer navigation" className="flex flex-wrap gap-x-6 gap-y-3 text-sm text-white/75">
          <a className="transition hover:text-white" href="#home">Home</a>
          <a className="transition hover:text-white" href="#how-it-works">How It Works</a>
          <a className="transition hover:text-white" href="#features">Features</a>
          <a className="transition hover:text-white" href="#privacy" id="privacy">Privacy Policy</a>
          <a className="transition hover:text-white" href="#disclaimer">Disclaimer</a>
        </nav>
      </div>
      <div className="border-t border-white/10">
        <p className="mx-auto max-w-7xl px-5 py-5 text-xs text-white/50 sm:px-8 lg:px-10">
          © 2026 IngredientIQ. For educational purposes only.
        </p>
      </div>
    </footer>
  )
}

export default Footer
