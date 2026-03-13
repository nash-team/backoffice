import { useEffect, useState, useCallback, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useAppDispatch, useAppSelector } from '../../../../app/hooks'
import { ProgressBar } from '../../../../shared/components/ProgressBar'
import { showToast } from '../../../../shared/components/Toast'
import { useFileDownload } from '../../../../shared/hooks/useFileDownload'
import { useRegenWebSocket } from '../../../../shared/hooks/useRegenWebSocket'
import { selectCurrentEbook, selectEbookLoading, selectProgress } from '../../store/selectors/ebook-selectors'
import { getEbookDetail } from '../../domain/usecases/ebook-usecases'
import { exportEbook, type ExportType } from '../../domain/usecases/export-usecases'
import { clearCurrentEbook } from '../../store/slices/ebook-slice'
import { PageGrid } from '../components/PageGrid'
import { PageEditModal } from '../components/PageEditModal'
import { ActionToolbar } from '../components/ActionToolbar'
import { KdpCoverPreviewModal } from '../components/KdpCoverPreviewModal'

export function EbookDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const dispatch = useAppDispatch()
  const ebook = useAppSelector(selectCurrentEbook)
  const loading = useAppSelector(selectEbookLoading)
  const progress = useAppSelector(selectProgress)
  const download = useFileDownload()

  const [selectedPages, setSelectedPages] = useState<Set<number>>(new Set())
  const [showKdpPreview, setShowKdpPreview] = useState(false)

  useRegenWebSocket(ebook?.id)

  useEffect(() => {
    if (id) dispatch(getEbookDetail(Number(id)))
    return () => { dispatch(clearCurrentEbook()) }
  }, [id, dispatch])

  const handleTogglePage = useCallback((pageIndex: number) => {
    setSelectedPages((prev) => {
      const next = new Set(prev)
      if (next.has(pageIndex)) next.delete(pageIndex)
      else next.add(pageIndex)
      return next
    })
  }, [])

  const handleClearSelection = useCallback(() => setSelectedPages(new Set()), [])

  async function handleExport(type: ExportType) {
    if (!ebook) return
    try {
      const result = await dispatch(exportEbook({ ebookId: ebook.id, type })).unwrap()
      const ext = type === 'kdp-cover' ? 'png' : 'pdf'
      download(result.blob, `${ebook.title}-${type}.${ext}`)
      showToast('success', 'Download started')
    } catch (err) {
      showToast('error', `Export failed: ${err instanceof Error ? err.message : 'Unknown error'}`)
    }
  }

  if (loading && !ebook) {
    return <p className="py-8 text-center text-neutral-400">Loading...</p>
  }

  if (!ebook) {
    return <p className="py-8 text-center text-neutral-400">Ebook not found</p>
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <button
            onClick={() => navigate('/')}
            className="mb-2 text-sm text-neutral-500 hover:text-neutral-700"
          >
            &larr; Back to dashboard
          </button>
          <h1 className="text-2xl font-bold text-neutral-900">{ebook.title}</h1>
          <div className="mt-2 flex items-center gap-3 text-sm text-neutral-500">
            <span>Theme: {ebook.theme}</span>
            <span>Pages: {ebook.num_pages}</span>
            {ebook.created_at && (
              <span>Created: {new Date(ebook.created_at).toLocaleDateString()}</span>
            )}
          </div>
        </div>

        {/* Actions */}
        <div className="flex gap-2">
          <ExportDropdown onExport={handleExport} />
        </div>
      </div>

      {/* Progress bar */}
      {progress && progress.state === 'running' && (
        <ProgressBar
          value={progress.status}
          label={`Generating page ${progress.pageIndex}...`}
        />
      )}

      {/* Action toolbar */}
      <ActionToolbar
        ebook={ebook}
        selectedPages={selectedPages}
        onClearSelection={handleClearSelection}
        onShowKdpPreview={() => setShowKdpPreview(true)}
      />

      {/* Page grid with selection */}
      <PageGrid
        ebook={ebook}
        selectedPages={selectedPages}
        onTogglePage={handleTogglePage}
      />

      {/* Modals */}
      <PageEditModal />
      {showKdpPreview && (
        <KdpCoverPreviewModal
          open={showKdpPreview}
          onClose={() => setShowKdpPreview(false)}
          ebookId={ebook.id}
        />
      )}
    </div>
  )
}

function ExportDropdown({ onExport }: { onExport: (type: ExportType) => void }) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    function handleClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [open])

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen(!open)}
        className="rounded-lg border border-neutral-300 px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50"
      >
        Export
      </button>
      {open && (
        <div className="absolute right-0 z-10 mt-1 w-48 rounded-lg border border-neutral-200 bg-white py-1 shadow-lg">
          {[
            { type: 'pdf' as const, label: 'Download PDF' },
            { type: 'kdp-interior' as const, label: 'KDP Interior' },
            { type: 'kdp-cover' as const, label: 'KDP Cover (PNG)' },
            { type: 'kdp-full' as const, label: 'KDP Full Package' },
          ].map((item) => (
            <button
              key={item.type}
              onClick={() => { onExport(item.type); setOpen(false) }}
              className="block w-full px-4 py-2 text-left text-sm text-neutral-700 hover:bg-neutral-50"
            >
              {item.label}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
