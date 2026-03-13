import { useEffect, useState } from 'react'
import { useAppDispatch } from '../../../../app/hooks'
import { Modal } from '../../../../shared/components/Modal'
import { fetchKdpCoverPreview } from '../../domain/usecases/export-usecases'

interface KdpCoverPreviewModalProps {
  open: boolean
  onClose: () => void
  ebookId: number
}

export function KdpCoverPreviewModal({ open, onClose, ebookId }: KdpCoverPreviewModalProps) {
  const dispatch = useAppDispatch()
  const [imageUrl, setImageUrl] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!open) return

    let cancelled = false
    setLoading(true)
    setError(null)

    dispatch(fetchKdpCoverPreview(ebookId))
      .unwrap()
      .then((blob) => {
        if (!cancelled) setImageUrl(URL.createObjectURL(blob))
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Failed to load preview')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [open, ebookId, dispatch])

  // Cleanup blob URL on unmount
  useEffect(() => {
    return () => {
      if (imageUrl) URL.revokeObjectURL(imageUrl)
    }
  }, [imageUrl])

  return (
    <Modal open={open} onClose={onClose} title="KDP Cover Preview" size="full">
      <div className="flex min-h-0 flex-1 items-center justify-center">
        {loading && (
          <div className="text-center">
            <div className="mx-auto mb-2 h-8 w-8 animate-spin rounded-full border-4 border-neutral-300 border-t-primary-600" />
            <p className="text-sm text-neutral-500">Generating KDP cover preview...</p>
          </div>
        )}
        {error && (
          <div className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}
        {imageUrl && !loading && (
          <img
            src={imageUrl}
            alt="KDP Cover Preview with template overlay"
            className="max-h-full max-w-full object-contain"
          />
        )}
      </div>
      <p className="mt-2 shrink-0 text-center text-xs text-neutral-400">
        Template overlay shows safe zones, trim marks, and spine width
      </p>
    </Modal>
  )
}
