import { useWindowManager } from '@/context/WindowManagerContext'

interface DataBrowserLinkProps {
  model: string
  id?: number
  className?: string
  children?: React.ReactNode
}

/**
 * Opens the record in DataBrowser. Uses the window manager for in-app navigation.
 */
export default function DataBrowserLink({ model, id, className, children }: DataBrowserLinkProps) {
  const { ensureWindow, activateWindow } = useWindowManager()

  const handleClick = () => {
    const path = `/admin-wb?model=${model}${id ? `&id=${id}` : ''}`
    ensureWindow(path, `${model}${id ? ` #${id}` : ''}`)
    activateWindow(path)
  }

  return (
    <button
      onClick={handleClick}
      className={className || 'inline-flex items-center gap-1 text-xs text-gray-500 hover:text-blue-600 transition-colors dark:text-gray-400 dark:hover:text-blue-400'}
      title={`Open ${model}${id ? ` #${id}` : ''} in DataBrowser`}
    >
      {children || (
        <>
          <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
          </svg>
          <span>DataBrowser</span>
        </>
      )}
    </button>
  )
}
