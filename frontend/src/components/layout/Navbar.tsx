import { ArrowUpRight, Leaf } from 'lucide-react'
import Button from '../ui/Button'

function Navbar() {
  return (
    <header className="sticky top-0 z-50 border-b border-[#e9e7df]/80 bg-[#FAF9F6]/90 backdrop-blur-xl">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-x-5 gap-y-3 px-5 py-4 sm:px-8 lg:px-10">
        <a
          aria-label="IngredientIQ home"
          className="flex shrink-0 items-center gap-2.5"
          href="#home"
        >
          <span className="grid size-10 place-items-center rounded-full bg-[#e5ece5] text-[#294B3A]">
            <Leaf aria-hidden="true" size={20} strokeWidth={1.8} />
          </span>
          <span className="font-display text-xl font-semibold tracking-tight text-[#294B3A]">
            Ingredient<span className="text-[#8FAF9B]">IQ</span>
          </span>
        </a>

        <nav
          aria-label="Main navigation"
          className="order-3 flex w-full items-center justify-center gap-6 border-t border-[#e9e7df] pt-3 text-sm text-[#626760] sm:order-2 sm:w-auto sm:justify-start sm:border-0 sm:pt-0"
        >
          <a className="transition hover:text-[#294B3A]" href="#home">
            Home
          </a>
          <a className="transition hover:text-[#294B3A]" href="#how-it-works">
            How It Works
          </a>
          <a className="transition hover:text-[#294B3A]" href="#features">
            Features
          </a>
        </nav>

        <Button
          className="min-h-10 shrink-0 px-4 py-2 text-xs sm:min-h-11 sm:px-5 sm:text-sm"
          href="#analyzer"
        >
          <span className="sm:hidden">Analyze</span>
          <span className="hidden sm:inline">Analyze Ingredients</span>
          <ArrowUpRight aria-hidden="true" size={16} />
        </Button>
      </div>
    </header>
  )
}

export default Navbar
