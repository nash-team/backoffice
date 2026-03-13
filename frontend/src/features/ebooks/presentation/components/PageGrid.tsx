import { useEffect, useState } from 'react'
import { useAppDispatch } from '../../../../app/hooks'
import type { Ebook } from '../../domain/entities/ebook'
import { fetchPageImage } from '../../domain/usecases/export-usecases'
import { openEditModal } from '../../store/slices/regeneration-slice'

interface PageGridProps {
  ebook: Ebook
  selectedPages: Set<number>
  onTogglePage: (pageIndex: number) => void
}

export function PageGrid({ ebook, selectedPages, onTogglePage }: PageGridProps) {
  const dispatch = useAppDispatch()
  const pages = ebook.pages_meta ?? []

  if (pages.length === 0) {
    return <p className="py-8 text-center text-neutral-400">No pages available</p>
  }

  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5">
      {pages.map((page) => {
        const isCover = page.page_number === 0
        const isBackCover = page.page_number === pages.length - 1
        const isSelectable = !isCover && !isBackCover

        return (
          <PageThumbnail
            key={`${page.page_number}-${page.title}`}
            ebookId={ebook.id}
            pageIndex={page.page_number}
            title={page.title}
            isCover={isCover}
            isBackCover={isBackCover}
            selected={selectedPages.has(page.page_number)}
            selectable={isSelectable}
            onToggleSelect={() => onTogglePage(page.page_number)}
            onEdit={() =>
              dispatch(
                openEditModal({
                  ebookId: ebook.id,
                  pageIndex: page.page_number,
                  isCover,
                }),
              )
            }
          />
        )
      })}
    </div>
  )
}

function PageThumbnail({
  ebookId,
  pageIndex,
  title,
  isCover,
  isBackCover,
  selected,
  selectable,
  onToggleSelect,
  onEdit,
}: {
  ebookId: number
  pageIndex: number
  title: string
  isCover: boolean
  isBackCover: boolean
  selected: boolean
  selectable: boolean
  onToggleSelect: () => void
  onEdit: () => void
}) {
  const dispatch = useAppDispatch()
  const [imageBase64, setImageBase64] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(false)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(false)
    dispatch(fetchPageImage({ ebookId, pageIndex }))
      .unwrap()
      .then((data) => {
        if (!cancelled) setImageBase64(data.imageBase64)
      })
      .catch(() => {
        if (!cancelled) setError(true)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => { cancelled = true }
  }, [ebookId, pageIndex, dispatch])

  const label = isCover ? 'Cover' : isBackCover ? 'Back Cover' : title

  return (
    <div
      className={`group relative overflow-hidden rounded-lg border-2 bg-white transition-all ${
        selected ? 'border-primary-500 ring-2 ring-primary-200' : 'border-neutral-200'
      }`}
    >
      {/* Checkbox for content pages */}
      {selectable && (
        <label
          className="absolute left-2 top-2 z-10 cursor-pointer"
          onClick={(e) => e.stopPropagation()}
        >
          <input
            type="checkbox"
            checked={selected}
            onChange={onToggleSelect}
            className="h-4 w-4 rounded border-neutral-300 text-primary-600 focus:ring-primary-500"
          />
        </label>
      )}

      {/* Image */}
      <button onClick={onEdit} className="block w-full text-left">
        <div className="aspect-[4/5] w-full bg-neutral-100">
          {loading && (
            <div className="flex h-full items-center justify-center text-neutral-400">
              Loading...
            </div>
          )}
          {error && !loading && (
            <div className="flex h-full items-center justify-center text-neutral-400">
              Failed to load
            </div>
          )}
          {imageBase64 && (
            <img
              src={`data:image/png;base64,${imageBase64}`}
              alt={label}
              className="h-full w-full object-contain"
            />
          )}
        </div>
      </button>

      {/* Label */}
      <div className="border-t border-neutral-100 px-2 py-1.5">
        <p className="truncate text-xs text-neutral-600">{label}</p>
      </div>

      {/* Hover overlay */}
      <button
        onClick={onEdit}
        className="absolute inset-0 flex items-center justify-center bg-black/0 transition-colors group-hover:bg-black/10"
      >
        <span className="rounded bg-white/90 px-2 py-1 text-xs font-medium opacity-0 shadow transition-opacity group-hover:opacity-100">
          Edit
        </span>
      </button>
    </div>
  )
}
