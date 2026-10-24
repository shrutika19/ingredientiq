import { useEffect, useRef, useState } from 'react'
import {
  ImagePlus,
  LoaderCircle,
  RotateCcw,
  Sparkles,
  Trash2,
  UploadCloud,
} from 'lucide-react'
import { extractIngredientsFromImage } from '../../api/imageExtraction'
import Button from '../ui/Button'

const MAX_FILE_SIZE = 5 * 1024 * 1024
const ALLOWED_TYPES = ['image/jpeg', 'image/png', 'image/webp']

interface UploadImageTabProps {
  isSubmitting: boolean
  onAnalyze: (ingredientText: string) => void
}

function UploadImageTab({ isSubmitting, onAnalyze }: UploadImageTabProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const previewUrlRef = useRef<string | null>(null)
  const [file, setFile] = useState<File | null>(null)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [isDragging, setIsDragging] = useState(false)
  const [isExtracting, setIsExtracting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [ingredientText, setIngredientText] = useState<string | null>(null)
  const [warnings, setWarnings] = useState<string[]>([])

  useEffect(
    () => () => {
      if (previewUrlRef.current) {
        URL.revokeObjectURL(previewUrlRef.current)
      }
    },
    [],
  )

  function updatePreview(nextFile: File | null) {
    if (previewUrlRef.current) {
      URL.revokeObjectURL(previewUrlRef.current)
    }

    const nextUrl = nextFile ? URL.createObjectURL(nextFile) : null
    previewUrlRef.current = nextUrl
    setPreviewUrl(nextUrl)
  }

  function chooseFile(nextFile: File | undefined) {
    if (!nextFile) {
      return
    }

    if (!ALLOWED_TYPES.includes(nextFile.type)) {
      setFile(null)
      updatePreview(null)
      setIngredientText(null)
      setWarnings([])
      setError('Choose a JPG, PNG, or WEBP image.')
      return
    }

    if (nextFile.size > MAX_FILE_SIZE) {
      setFile(null)
      updatePreview(null)
      setIngredientText(null)
      setWarnings([])
      setError('The image must be 5 MB or smaller.')
      return
    }

    setFile(nextFile)
    updatePreview(nextFile)
    setError(null)
    setIngredientText(null)
    setWarnings([])
  }

  async function handleExtract() {
    if (!file || isExtracting) {
      return
    }

    setIsExtracting(true)
    setError(null)
    setIngredientText(null)
    setWarnings([])

    try {
      const result = await extractIngredientsFromImage(file)
      setIngredientText(result.ingredient_text)
      setWarnings(result.warnings)
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : 'Could not extract ingredients from this image. Please try again.',
      )
    } finally {
      setIsExtracting(false)
    }
  }

  function removeFile() {
    setFile(null)
    updatePreview(null)
    setError(null)
    setIngredientText(null)
    setWarnings([])
    if (inputRef.current) {
      inputRef.current.value = ''
    }
  }

  const isBusy = isSubmitting || isExtracting
  const hasExtractedText = Boolean(ingredientText?.trim())

  return (
    <div
      aria-labelledby="upload-tab"
      className="p-6 sm:p-8 md:p-10"
      id="upload-panel"
      role="tabpanel"
    >
      <input
        accept="image/jpeg,image/png,image/webp"
        className="sr-only"
        disabled={isBusy}
        onChange={(event) => {
          chooseFile(event.target.files?.[0])
          event.target.value = ''
        }}
        ref={inputRef}
        type="file"
      />
      <p className="text-sm font-semibold text-[#343a34]">
        Have a product label?
      </p>
      <p className="mt-1 text-xs text-[#898c85]">
        Upload a clear photo to extract and review its ingredient list.
      </p>
      <div
        className={`mt-5 flex min-h-48 flex-col items-center justify-center rounded-2xl border border-dashed px-5 text-center ${
          isDragging
            ? 'border-[#54735b] bg-[#f0f5ee]'
            : 'border-[#cbd7ca] bg-[#fafbf8]'
        }`}
        onDragEnter={(event) => {
          event.preventDefault()
          setIsDragging(true)
        }}
        onDragLeave={(event) => {
          event.preventDefault()
          if (!event.currentTarget.contains(event.relatedTarget as Node | null)) {
            setIsDragging(false)
          }
        }}
        onDragOver={(event) => event.preventDefault()}
        onDrop={(event) => {
          event.preventDefault()
          setIsDragging(false)
          if (!isBusy) {
            chooseFile(event.dataTransfer.files[0])
          }
        }}
      >
        {previewUrl ? (
          <img
            alt={`Preview of ${file?.name ?? 'uploaded product label'}`}
            className="max-h-56 max-w-full rounded-xl object-contain"
            src={previewUrl}
          />
        ) : (
          <>
            <span className="grid size-12 place-items-center rounded-full bg-[#eaf0e8] text-[#54735b]">
              <UploadCloud aria-hidden="true" size={22} strokeWidth={1.8} />
            </span>
            <p className="mt-3 text-sm font-semibold text-[#3f4940]">
              Drop your product label here
            </p>
            <p className="mt-1 text-xs text-[#898c85]">
              or choose an image from your device
            </p>
            <Button
              className="mt-4 min-h-10 px-4 py-2 text-xs"
              disabled={isBusy}
              onClick={() => inputRef.current?.click()}
              variant="secondary"
            >
              <ImagePlus aria-hidden="true" size={15} />
              Browse Files
            </Button>
            <p className="mt-3 text-[10px] tracking-wide text-[#a0a39c]">
              JPG, PNG, WEBP · MAX 5 MB
            </p>
          </>
        )}
      </div>
      {file && (
        <div className="mt-3 flex items-center justify-between gap-3 text-xs text-[#62685f]">
          <p className="min-w-0 truncate" title={file.name}>
            {file.name}
          </p>
          <div className="flex shrink-0 gap-2">
            <Button
              className="min-h-9 px-3 py-1.5 text-xs"
              disabled={isBusy}
              onClick={() => inputRef.current?.click()}
              variant="secondary"
            >
              <ImagePlus aria-hidden="true" size={14} />
              Replace
            </Button>
            <Button
              aria-label="Remove uploaded image"
              className="min-h-9 px-3 py-1.5 text-xs"
              disabled={isBusy}
              onClick={removeFile}
              variant="secondary"
            >
              <Trash2 aria-hidden="true" size={14} />
              Remove
            </Button>
          </div>
        </div>
      )}

      {error && (
        <div className="mt-4 rounded-xl border border-[#f0c9c4] bg-[#fff1ef] p-3 text-sm text-[#8b342c]" role="alert">
          <p>{error}</p>
        </div>
      )}

      {isExtracting && (
        <p className="mt-4 flex items-center justify-center gap-2 text-sm text-[#62685f]" role="status">
          <LoaderCircle aria-hidden="true" className="animate-spin" size={17} />
          Extracting ingredients from your image…
        </p>
      )}

      {ingredientText !== null && (
        <div className="mt-5">
          <label
            className="block text-sm font-semibold text-[#343a34]"
            htmlFor="extracted-ingredients"
          >
            Review extracted ingredients
          </label>
          <p className="mt-1 text-xs text-[#898c85]">
            Check the text for accuracy and edit it before analysis.
          </p>
          <textarea
            className="mt-3 min-h-36 w-full resize-y rounded-2xl border border-[#e5e7e0] bg-[#fcfcfa] p-4 text-sm leading-6 text-[#41463f] outline-none placeholder:text-[#a3a69f] focus:border-[#8FAF9B] focus:ring-4 focus:ring-[#8FAF9B]/15"
            id="extracted-ingredients"
            onChange={(event) => setIngredientText(event.target.value)}
            placeholder="Extracted ingredient text will appear here..."
            value={ingredientText}
          />
          {warnings.map((warning) => (
            <p className="mt-2 text-sm text-[#8b5a24]" key={warning} role="status">
              {warning}
            </p>
          ))}
        </div>
      )}

      {file && ingredientText === null && !isExtracting && (
        <Button
          className="mt-5 w-full disabled:cursor-not-allowed disabled:opacity-60"
          disabled={isBusy}
          onClick={() => void handleExtract()}
          type="button"
        >
          {error ? (
            <RotateCcw aria-hidden="true" size={16} />
          ) : (
            <Sparkles aria-hidden="true" size={16} />
          )}
          {error ? 'Retry extraction' : 'Extract Ingredients'}
        </Button>
      )}
      {ingredientText !== null && (
        <Button
          className="mt-5 w-full disabled:cursor-not-allowed disabled:opacity-60"
          disabled={!hasExtractedText || isBusy}
          onClick={() => onAnalyze(ingredientText)}
          type="button"
        >
          <Sparkles aria-hidden="true" size={16} />
          {isSubmitting ? 'Analyzing Ingredients…' : 'Analyze Ingredients'}
        </Button>
      )}
    </div>
  )
}

export default UploadImageTab
