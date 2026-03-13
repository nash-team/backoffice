import { useEffect, useState } from 'react'

export interface ToastMessage {
  id: string
  type: 'success' | 'error' | 'info'
  text: string
}

const typeStyles: Record<ToastMessage['type'], string> = {
  success: 'bg-primary-600 text-white',
  error: 'bg-red-600 text-white',
  info: 'bg-blue-600 text-white',
}

interface ToastProps {
  message: ToastMessage
  onDismiss: (id: string) => void
}

function Toast({ message, onDismiss }: ToastProps) {
  useEffect(() => {
    const timer = setTimeout(() => onDismiss(message.id), 4000)
    return () => clearTimeout(timer)
  }, [message.id, onDismiss])

  return (
    <div
      className={`rounded-lg px-4 py-3 text-sm font-medium shadow-lg ${typeStyles[message.type]}`}
    >
      {message.text}
    </div>
  )
}

export function ToastContainer() {
  const [toasts, setToasts] = useState<ToastMessage[]>([])

  useEffect(() => {
    const handler = (e: CustomEvent<ToastMessage>) => {
      setToasts((prev) => [...prev, e.detail])
    }
    window.addEventListener('toast', handler as EventListener)
    return () => window.removeEventListener('toast', handler as EventListener)
  }, [])

  const dismiss = (id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }

  if (toasts.length === 0) return null

  return (
    <div className="fixed right-4 top-4 z-50 flex flex-col gap-2">
      {toasts.map((t) => (
        <Toast key={t.id} message={t} onDismiss={dismiss} />
      ))}
    </div>
  )
}

export function showToast(type: ToastMessage['type'], text: string) {
  const id = crypto.randomUUID()
  window.dispatchEvent(
    new CustomEvent('toast', { detail: { id, type, text } }),
  )
}
