import { useEffect } from 'react'
import { CheckCircle2, CircleX, X } from 'lucide-react'

export type ToastKind = 'success' | 'error'

interface ToastProps {
  kind: ToastKind
  message: string
  onClose: () => void
  duration?: number
}

function Toast({ kind, message, onClose, duration = 5000 }: ToastProps) {
  useEffect(() => {
    const timeoutId = window.setTimeout(onClose, duration)
    return () => window.clearTimeout(timeoutId)
  }, [duration, onClose])

  const isSuccess = kind === 'success'

  return (
    <div
      aria-live={isSuccess ? 'polite' : 'assertive'}
      className={`fixed bottom-5 right-5 z-50 flex w-[calc(100%-2.5rem)] max-w-sm items-start gap-3 rounded-2xl border p-4 shadow-[0_16px_45px_-18px_rgba(24,35,27,0.35)] ${
        isSuccess
          ? 'border-[#c7dfca] bg-[#edf7ee] text-[#285c34]'
          : 'border-[#f0c9c4] bg-[#fff1ef] text-[#8b342c]'
      }`}
      role={isSuccess ? 'status' : 'alert'}
    >
      {isSuccess ? (
        <CheckCircle2 aria-hidden="true" className="mt-0.5 shrink-0" size={20} />
      ) : (
        <CircleX aria-hidden="true" className="mt-0.5 shrink-0" size={20} />
      )}
      <p className="min-w-0 flex-1 text-sm font-medium leading-6">{message}</p>
      <button
        aria-label="Close notification"
        className="ml-1 -mr-1 -mt-1 rounded-full p-1.5 opacity-75 transition hover:bg-black/5 hover:opacity-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2"
        onClick={onClose}
        type="button"
      >
        <X aria-hidden="true" size={17} />
      </button>
    </div>
  )
}

export default Toast
