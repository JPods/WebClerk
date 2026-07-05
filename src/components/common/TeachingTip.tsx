import { useState } from 'react'
import { X } from 'lucide-react'

interface TeachingTipProps {
  id: string
  title: string
  body: string
  children: React.ReactNode
}

export function TeachingTip({ id, title, body, children }: TeachingTipProps) {
  const key = `wc3-tip-${id}`
  const [dismissed, setDismissed] = useState(() => localStorage.getItem(key) === '1')

  if (dismissed) return <>{children}</>

  const dismiss = () => {
    localStorage.setItem(key, '1')
    setDismissed(true)
  }

  return (
    <div className="relative">
      {children}
      <div className="absolute top-full left-0 mt-2 z-50 bg-blue-600 text-white rounded-lg p-3 shadow-lg max-w-xs">
        <button onClick={dismiss} className="absolute top-2 right-2 text-white/70 hover:text-white">
          <X size={14} />
        </button>
        <p className="font-semibold text-sm">{title}</p>
        <p className="text-xs text-white/80 mt-1">{body}</p>
      </div>
    </div>
  )
}
