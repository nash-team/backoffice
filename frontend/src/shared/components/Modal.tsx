import { useEffect, useRef, type ReactNode } from 'react'

interface ModalProps {
  open: boolean
  onClose: () => void
  title: string
  children: ReactNode
  size?: 'sm' | 'md' | 'lg' | 'full'
}

const sizeClasses = {
  sm: 'max-w-md',
  md: 'max-w-lg',
  lg: 'max-w-4xl h-[90vh]',
  full: 'max-w-[90vw] h-[90vh]',
}

export function Modal({ open, onClose, title, children, size = 'md' }: ModalProps) {
  const dialogRef = useRef<HTMLDialogElement>(null)

  useEffect(() => {
    const dialog = dialogRef.current
    if (!dialog) return

    if (open) {
      dialog.showModal()
    } else {
      dialog.close()
    }
  }, [open])

  if (!open) return null

  return (
    <dialog
      ref={dialogRef}
      onClose={onClose}
      className={`m-auto flex max-h-[90vh] w-full ${sizeClasses[size]} flex-col rounded-lg bg-white p-0 shadow-xl backdrop:bg-black/50`}
    >
      <div className="flex shrink-0 items-center justify-between border-b border-neutral-200 px-6 py-4">
        <h2 className="text-lg font-semibold text-neutral-900">{title}</h2>
        <button
          onClick={onClose}
          className="text-neutral-400 hover:text-neutral-600"
        >
          ✕
        </button>
      </div>
      <div className="flex min-h-0 flex-1 flex-col p-6">{children}</div>
    </dialog>
  )
}
