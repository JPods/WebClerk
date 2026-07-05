import { useState } from 'react'
import { useWindowManager } from '@/context/WindowManagerContext'

interface QuickAction {
  label: string
  path: string
}

const actions: QuickAction[] = [
  { label: 'New Order', path: '/admin-wb?model=order&action=new' },
  { label: 'New Proposal', path: '/admin-wb?model=proposal&action=new' },
  { label: 'New Purchase', path: '/admin-wb?model=purchase&action=new' },
  { label: 'New Customer', path: '/admin-wb?model=customer&action=new' },
  { label: 'New Contact', path: '/admin-wb?model=contact&action=new' },
]

export default function QuickCreate() {
  const [open, setOpen] = useState(false)
  const { ensureWindow, activateWindow } = useWindowManager()

  const handleClick = (action: QuickAction) => {
    ensureWindow(action.path, action.label)
    activateWindow(action.path)
    setOpen(false)
  }

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1.5 rounded-lg bg-blue-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-700 transition-colors"
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
        </svg>
        <span className="hidden sm:inline">Quick Create</span>
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
          <div className="absolute right-0 top-full mt-2 z-50 w-48 rounded-lg border border-gray-200 bg-white shadow-lg overflow-hidden dark:border-gray-700 dark:bg-gray-900">
            {actions.map(action => (
              <button
                key={action.path}
                onClick={() => handleClick(action)}
                className="flex w-full items-center px-4 py-2.5 text-sm text-gray-700 hover:bg-gray-50 transition-colors dark:text-gray-300 dark:hover:bg-gray-800"
              >
                {action.label}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
