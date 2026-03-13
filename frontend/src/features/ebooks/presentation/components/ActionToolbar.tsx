import { useState } from 'react'
import { useAppDispatch, useAppSelector } from '../../../../app/hooks'
import { showToast } from '../../../../shared/components/Toast'
import { selectBulkAction } from '../../store/selectors/ebook-selectors'
import { regeneratePages, completePages, addNewPages } from '../../domain/usecases/regeneration-usecases'
import { getEbookDetail } from '../../domain/usecases/ebook-usecases'
import type { Ebook } from '../../domain/entities/ebook'

interface ActionToolbarProps {
  ebook: Ebook
  selectedPages: Set<number>
  onClearSelection: () => void
  onShowKdpPreview: () => void
}

export function ActionToolbar({ ebook, selectedPages, onClearSelection, onShowKdpPreview }: ActionToolbarProps) {
  const dispatch = useAppDispatch()
  const bulkAction = useAppSelector(selectBulkAction)
  const [addCount, setAddCount] = useState(1)

  const totalPages = ebook.pages_meta?.length ?? 0
  const needsCompletion = totalPages < 24
  const maxAddable = Math.max(0, 100 - totalPages)

  async function handleRegenerate(type: 'cover' | 'back_cover' | 'content_page') {
    try {
      const pageIndices = type === 'content_page' ? [...selectedPages] : undefined
      await dispatch(regeneratePages({ ebookId: ebook.id, pageType: type, pageIndices })).unwrap()
      showToast('success', type === 'cover' ? 'Cover regenerated' : type === 'back_cover' ? 'Back cover regenerated' : `${selectedPages.size} page(s) regenerated`)
      onClearSelection()
      dispatch(getEbookDetail(ebook.id))
    } catch {
      showToast('error', 'Regeneration failed')
    }
  }

  async function handleCompletePages() {
    try {
      const result = await dispatch(completePages({ ebookId: ebook.id })).unwrap()
      showToast('success', result.message)
      dispatch(getEbookDetail(ebook.id))
    } catch {
      showToast('error', 'Failed to complete pages')
    }
  }

  async function handleAddPages() {
    if (addCount < 1 || addCount > maxAddable) return
    try {
      const result = await dispatch(addNewPages({ ebookId: ebook.id, count: addCount })).unwrap()
      showToast('success', result.message)
      dispatch(getEbookDetail(ebook.id))
      if (result.limit_reached) showToast('info', 'Page limit reached (100)')
    } catch {
      showToast('error', 'Failed to add pages')
    }
  }

  return (
    <div className="flex flex-wrap items-center gap-2 rounded-lg border border-neutral-200 bg-neutral-50 p-3">
      {/* Regeneration */}
      <div className="flex items-center gap-2">
        <span className="text-xs font-medium uppercase tracking-wider text-neutral-400">Regenerate</span>
        <button
          onClick={() => handleRegenerate('cover')}
          disabled={bulkAction.loading}
          className="rounded-md bg-amber-500 px-3 py-1.5 text-xs font-medium text-white hover:bg-amber-600 disabled:opacity-50"
        >
          Cover
        </button>
        <button
          onClick={() => handleRegenerate('back_cover')}
          disabled={bulkAction.loading}
          className="rounded-md bg-amber-500 px-3 py-1.5 text-xs font-medium text-white hover:bg-amber-600 disabled:opacity-50"
        >
          Back Cover
        </button>
        <button
          onClick={() => handleRegenerate('content_page')}
          disabled={bulkAction.loading || selectedPages.size === 0}
          className="rounded-md bg-amber-500 px-3 py-1.5 text-xs font-medium text-white hover:bg-amber-600 disabled:opacity-50"
          title={selectedPages.size === 0 ? 'Select pages first' : `Regenerate ${selectedPages.size} page(s)`}
        >
          Selected ({selectedPages.size})
        </button>
      </div>

      <div className="h-6 w-px bg-neutral-300" />

      {/* Pages management */}
      <div className="flex items-center gap-2">
        {needsCompletion && (
          <button
            onClick={handleCompletePages}
            disabled={bulkAction.loading}
            className="rounded-md bg-sky-500 px-3 py-1.5 text-xs font-medium text-white hover:bg-sky-600 disabled:opacity-50"
          >
            Complete to 24p
          </button>
        )}
        {maxAddable > 0 && (
          <div className="flex items-center gap-1">
            <input
              type="number"
              min={1}
              max={maxAddable}
              value={addCount}
              onChange={(e) => setAddCount(Math.max(1, Math.min(maxAddable, Number(e.target.value))))}
              className="w-14 rounded-md border border-neutral-300 px-2 py-1 text-center text-xs"
            />
            <button
              onClick={handleAddPages}
              disabled={bulkAction.loading}
              className="rounded-md bg-emerald-500 px-3 py-1.5 text-xs font-medium text-white hover:bg-emerald-600 disabled:opacity-50"
            >
              + Add AI Pages
            </button>
          </div>
        )}
      </div>

      <div className="h-6 w-px bg-neutral-300" />

      {/* KDP Preview */}
      <button
        onClick={onShowKdpPreview}
        className="rounded-md border border-neutral-300 px-3 py-1.5 text-xs font-medium text-neutral-700 hover:bg-white"
      >
        KDP Cover Preview
      </button>

      {/* Loading indicator */}
      {bulkAction.loading && (
        <div className="flex items-center gap-2 text-xs text-neutral-500">
          <div className="h-4 w-4 animate-spin rounded-full border-2 border-neutral-300 border-t-primary-600" />
          Processing...
        </div>
      )}
    </div>
  )
}
