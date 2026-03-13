import { useEffect, useState } from 'react'
import { useAppDispatch } from '../../../../app/hooks'
import { listEbooks } from '../../domain/usecases/ebook-usecases'
import { EbookTable } from '../components/EbookTable'
import { PaginationControls } from '../components/PaginationControls'
import { CreateEbookModal } from '../components/CreateEbookModal'

export function DashboardPage() {
  const dispatch = useAppDispatch()
  const [createOpen, setCreateOpen] = useState(false)

  useEffect(() => {
    dispatch(listEbooks({ page: 1 }))
  }, [dispatch])

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-neutral-900">Dashboard</h1>
        <button
          onClick={() => setCreateOpen(true)}
          className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700"
        >
          + New Ebook
        </button>
      </div>

      <div className="space-y-4">
        <EbookTable />
        <PaginationControls />
      </div>

      <CreateEbookModal
        open={createOpen}
        onClose={() => setCreateOpen(false)}
      />
    </div>
  )
}
