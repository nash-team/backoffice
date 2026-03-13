import { useEffect, useState } from 'react'
import { useAppDispatch, useAppSelector } from '../../../../app/hooks'
import { Modal } from '../../../../shared/components/Modal'
import { showToast } from '../../../../shared/components/Toast'
import { selectEditModal, selectPageData, selectPreview, selectProgress } from '../../store/selectors/ebook-selectors'
import { closeEditModal, restorePreview } from '../../store/slices/regeneration-slice'
import {
  fetchPageData,
  previewRegenerate,
  editPage,
  applyEdit,
  previewRegenerateCover,
  editCover,
  applyCoverEdit,
} from '../../domain/usecases/regeneration-usecases'
import { getEbookDetail } from '../../domain/usecases/ebook-usecases'

type Mode = 'regenerate' | 'correct'

export function PageEditModal() {
  const dispatch = useAppDispatch()
  const modal = useAppSelector(selectEditModal)
  const pageData = useAppSelector(selectPageData)
  const preview = useAppSelector(selectPreview)
  const progress = useAppSelector(selectProgress)

  const [mode, setMode] = useState<Mode>('regenerate')
  const [regeneratePrompt, setRegeneratePrompt] = useState('')
  const [editPrompt, setEditPrompt] = useState('')
  const [previousImage, setPreviousImage] = useState<string | null>(null)
  const [applying, setApplying] = useState(false)

  // Load page data when modal opens
  useEffect(() => {
    if (modal.open && modal.ebookId !== null && modal.pageIndex !== null) {
      dispatch(fetchPageData({ ebookId: modal.ebookId, pageIndex: modal.pageIndex }))
    }
  }, [modal.open, modal.ebookId, modal.pageIndex, dispatch])

  // Pre-fill regenerate prompt from page data
  useEffect(() => {
    if (pageData.prompt) {
      setRegeneratePrompt(pageData.prompt)
    }
  }, [pageData.prompt])

  function handleClose() {
    dispatch(closeEditModal())
    setMode('regenerate')
    setRegeneratePrompt('')
    setEditPrompt('')
    setPreviousImage(null)
  }

  // Current displayed image (preview takes priority over original)
  const displayImage = preview.imageBase64 ?? pageData.imageBase64

  async function handlePreviewRegenerate() {
    if (modal.ebookId === null || modal.pageIndex === null) return

    // Save current image for undo
    if (displayImage) setPreviousImage(displayImage)

    const currentImage = displayImage ?? undefined
    if (modal.isCover) {
      await dispatch(previewRegenerateCover({ ebookId: modal.ebookId, customPrompt: regeneratePrompt || undefined, currentImage }))
    } else {
      await dispatch(previewRegenerate({ ebookId: modal.ebookId, pageIndex: modal.pageIndex, customPrompt: regeneratePrompt || undefined, currentImage }))
    }
  }

  async function handlePreviewEdit() {
    if (modal.ebookId === null || modal.pageIndex === null || !editPrompt.trim()) return

    // Save current image for undo
    if (displayImage) setPreviousImage(displayImage)

    const currentImage = displayImage ?? undefined
    if (modal.isCover) {
      await dispatch(editCover({ ebookId: modal.ebookId, editPrompt, currentImage }))
    } else {
      await dispatch(editPage({ ebookId: modal.ebookId, pageIndex: modal.pageIndex, editPrompt, currentImage }))
    }
  }

  function handleUndo() {
    if (!previousImage) return
    dispatch(restorePreview(previousImage))
    setPreviousImage(null)
  }

  async function handleApply() {
    if (modal.ebookId === null || modal.pageIndex === null) return
    const imageToApply = preview.imageBase64
    if (!imageToApply) return

    setApplying(true)
    try {
      if (modal.isCover) {
        await dispatch(applyCoverEdit({ ebookId: modal.ebookId, imageBase64: imageToApply })).unwrap()
      } else {
        await dispatch(applyEdit({ ebookId: modal.ebookId, pageIndex: modal.pageIndex, imageBase64: imageToApply })).unwrap()
      }
      showToast('success', 'Changes applied')
      dispatch(getEbookDetail(modal.ebookId))
      handleClose()
    } catch {
      showToast('error', 'Failed to apply changes')
    } finally {
      setApplying(false)
    }
  }

  const title = modal.isCover ? 'Edit Cover' : `Edit ${pageData.title ?? `Page ${modal.pageIndex}`}`
  const hasPreview = !!preview.imageBase64
  const canUndo = !!previousImage

  return (
    <Modal open={modal.open} onClose={handleClose} title={title} size="lg">
      <div className="flex min-h-0 flex-1 flex-col gap-3">
        {/* Image preview — flexible, shrinks to fit */}
        <div className="flex min-h-0 flex-1 items-center justify-center overflow-hidden rounded-lg border border-neutral-200 bg-neutral-50">
          {pageData.loading ? (
            <div className="text-neutral-400">Loading...</div>
          ) : preview.loading ? (
            <div className="text-center">
              <div className="mx-auto mb-2 h-8 w-8 animate-spin rounded-full border-4 border-neutral-300 border-t-primary-600" />
              <p className="text-sm text-neutral-500">
                {progress && progress.state === 'running'
                  ? `Generating... ${progress.status}%`
                  : 'Generating...'}
              </p>
            </div>
          ) : displayImage ? (
            <img
              src={`data:image/png;base64,${displayImage}`}
              alt={title}
              className="max-h-full max-w-full object-contain"
            />
          ) : (
            <div className="text-neutral-400">No image</div>
          )}
        </div>

        {/* Controls — fixed size, never shrink */}
        <div className="shrink-0 space-y-3">
          {/* Mode toggle */}
          <div className="flex rounded-lg border border-neutral-200">
            <button
              onClick={() => setMode('regenerate')}
              className={`flex-1 rounded-l-lg px-3 py-2 text-sm font-medium transition-colors ${
                mode === 'regenerate'
                  ? 'bg-primary-600 text-white'
                  : 'text-neutral-600 hover:bg-neutral-50'
              }`}
            >
              Regenerate
            </button>
            <button
              onClick={() => setMode('correct')}
              className={`flex-1 rounded-r-lg px-3 py-2 text-sm font-medium transition-colors ${
                mode === 'correct'
                  ? 'bg-primary-600 text-white'
                  : 'text-neutral-600 hover:bg-neutral-50'
              }`}
            >
              Correct
            </button>
          </div>

          {/* Regenerate mode */}
          {mode === 'regenerate' && (
            <div className="space-y-2">
              <label className="block text-sm font-medium text-neutral-700">Generation prompt</label>
              {!pageData.prompt && (
                <p className="text-xs text-amber-600">No saved prompt. Write a new one or leave empty for default.</p>
              )}
              <textarea
                value={regeneratePrompt}
                onChange={(e) => setRegeneratePrompt(e.target.value)}
                rows={3}
                placeholder="Describe the image you want..."
                className="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
              />
              <button
                onClick={handlePreviewRegenerate}
                disabled={preview.loading}
                className="rounded-lg bg-amber-500 px-4 py-2 text-sm font-medium text-white hover:bg-amber-600 disabled:opacity-50"
              >
                {preview.loading ? 'Generating...' : 'Preview'}
              </button>
            </div>
          )}

          {/* Correct mode */}
          {mode === 'correct' && (
            <div className="space-y-2">
              <label className="block text-sm font-medium text-neutral-700">Targeted correction</label>
              <textarea
                value={editPrompt}
                onChange={(e) => setEditPrompt(e.target.value)}
                rows={2}
                placeholder="e.g. remove the sun, fix the extra fingers..."
                className="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
              />
              <div className="flex gap-2">
                <button
                  onClick={handlePreviewEdit}
                  disabled={preview.loading || !editPrompt.trim()}
                  className="rounded-lg bg-sky-500 px-4 py-2 text-sm font-medium text-white hover:bg-sky-600 disabled:opacity-50"
                >
                  {preview.loading ? 'Generating...' : 'Preview'}
                </button>
                <button
                  onClick={handleUndo}
                  disabled={!canUndo || preview.loading}
                  className="rounded-lg border border-neutral-300 px-3 py-2 text-sm font-medium text-neutral-600 hover:bg-neutral-50 disabled:opacity-50"
                  title="Undo last change"
                >
                  Undo
                </button>
              </div>
            </div>
          )}

          {/* Info + Footer actions */}
          <div className="flex items-center justify-between border-t border-neutral-100 pt-3">
            <p className="text-xs text-neutral-400">
              Changes are only saved when you click "Apply".
            </p>
            <div className="flex gap-2">
              <button
                onClick={handleClose}
                className="rounded-lg border border-neutral-300 px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50"
              >
                Cancel
              </button>
              <button
                onClick={handleApply}
                disabled={applying || !hasPreview}
                className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
              >
                {applying ? 'Applying...' : 'Apply'}
              </button>
            </div>
          </div>
        </div>
      </div>
    </Modal>
  )
}
