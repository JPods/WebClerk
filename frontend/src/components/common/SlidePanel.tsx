import { useEffect, type ReactNode } from 'react'

interface SlidePanelProps {
  open: boolean
  onClose: () => void
  title?: string
  children: ReactNode
  width?: string
}

export default function SlidePanel({ open, onClose, title, children, width = 'max-w-lg' }: SlidePanelProps) {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    if (open) window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [open, onClose])

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <div
        className="absolute inset-0 bg-black/20 backdrop-blur-sm"
        onClick={onClose}
      />
      <div
        className={`relative w-full h-full bg-white dark:bg-gray-900 border-l border-gray-200 dark:border-gray-700 overflow-y-auto animate-slide-in-right ${width}`}
      >
        <div className="sticky top-0 z-10 flex items-center justify-between p-4 bg-white/95 dark:bg-gray-900/95 backdrop-blur border-b border-gray-200 dark:border-gray-700">
          {title && <h2 className="text-lg font-semibold text-gray-900 dark:text-white">{title}</h2>}
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-500 hover:text-gray-900 dark:hover:text-white transition-colors"
            aria-label="Close panel"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        <div className="p-4">
          {children}
        </div>
      </div>
    </div>
  )
}
