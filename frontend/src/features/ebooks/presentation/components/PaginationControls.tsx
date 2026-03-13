import { useAppDispatch, useAppSelector } from '../../../../app/hooks'
import { selectPagination } from '../../store/selectors/ebook-selectors'
import { setPage } from '../../store/slices/ebook-slice'
import { listEbooks } from '../../domain/usecases/ebook-usecases'

export function PaginationControls() {
  const dispatch = useAppDispatch()
  const { page, totalPages, total } = useAppSelector(selectPagination)

  if (totalPages <= 1) return null

  function goTo(p: number) {
    dispatch(setPage(p))
    dispatch(listEbooks({ page: p }))
  }

  // Build visible page numbers with ellipsis truncation
  function getVisiblePages(): Array<number | '...'> {
    if (totalPages <= 7) {
      return Array.from({ length: totalPages }, (_, i) => i + 1)
    }
    const pages: Array<number | '...'> = [1]
    if (page > 3) pages.push('...')
    for (let i = Math.max(2, page - 1); i <= Math.min(totalPages - 1, page + 1); i++) {
      pages.push(i)
    }
    if (page < totalPages - 2) pages.push('...')
    pages.push(totalPages)
    return pages
  }

  return (
    <div className="flex items-center justify-between border-t border-neutral-200 pt-4">
      <p className="text-sm text-neutral-500">
        {total} ebook{total !== 1 ? 's' : ''} total
      </p>
      <div className="flex gap-1">
        <button
          onClick={() => goTo(page - 1)}
          disabled={page <= 1}
          className="rounded-md border border-neutral-300 px-3 py-1.5 text-sm disabled:opacity-40"
        >
          Previous
        </button>
        {getVisiblePages().map((p, i) =>
          p === '...' ? (
            <span key={`ellipsis-${i}`} className="px-2 py-1.5 text-sm text-neutral-400">
              ...
            </span>
          ) : (
            <button
              key={p}
              onClick={() => goTo(p)}
              className={`rounded-md px-3 py-1.5 text-sm ${
                p === page
                  ? 'bg-primary-600 text-white'
                  : 'border border-neutral-300 hover:bg-neutral-50'
              }`}
            >
              {p}
            </button>
          ),
        )}
        <button
          onClick={() => goTo(page + 1)}
          disabled={page >= totalPages}
          className="rounded-md border border-neutral-300 px-3 py-1.5 text-sm disabled:opacity-40"
        >
          Next
        </button>
      </div>
    </div>
  )
}
