import { ImagePlus, Sparkles, UploadCloud } from 'lucide-react'
import Button from '../ui/Button'

function UploadImageTab() {
  return (
    <div
      aria-labelledby="upload-tab"
      className="p-6 sm:p-8 md:p-10"
      id="upload-panel"
      role="tabpanel"
    >
      <p className="text-sm font-semibold text-[#343a34]">
        Have a product label?
      </p>
      <p className="mt-1 text-xs text-[#898c85]">
        A clear photo helps make ingredients easier to read.
      </p>
      <div className="mt-5 flex min-h-48 flex-col items-center justify-center rounded-2xl border border-dashed border-[#cbd7ca] bg-[#fafbf8] px-5 text-center">
        <span className="grid size-12 place-items-center rounded-full bg-[#eaf0e8] text-[#54735b]">
          <UploadCloud aria-hidden="true" size={22} strokeWidth={1.8} />
        </span>
        <p className="mt-3 text-sm font-semibold text-[#3f4940]">
          Drop your product label here
        </p>
        <p className="mt-1 text-xs text-[#898c85]">
          or choose an image from your device
        </p>
        <Button className="mt-4 min-h-10 px-4 py-2 text-xs" variant="secondary">
          <ImagePlus aria-hidden="true" size={15} />
          Browse Files
        </Button>
        <p className="mt-3 text-[10px] tracking-wide text-[#a0a39c]">
          SUPPORTED FORMATS: JPG, PNG, WEBP
        </p>
      </div>
      <Button className="mt-5 w-full" type="button">
        <Sparkles aria-hidden="true" size={16} />
        Analyze Ingredients
      </Button>
    </div>
  )
}

export default UploadImageTab
