import { useNavigate } from 'react-router-dom'
import { useAppSelector } from '../../../../app/hooks'
import { selectEbooks, selectEbookLoading } from '../../store/selectors/ebook-selectors'

export function EbookTable() {
  const navigate = useNavigate()
  const ebooks = useAppSelector(selectEbooks)
  const loading = useAppSelector(selectEbookLoading)

  if (loading && ebooks.length === 0) {
    return <p className="py-8 text-center text-neutral-400">Loading...</p>
  }

  if (ebooks.length === 0) {
    return <p className="py-8 text-center text-neutral-400">No ebooks found</p>
  }

  return (
    <div className="overflow-hidden rounded-lg border border-neutral-200">
      <table className="w-full text-left text-sm">
        <thead className="border-b border-neutral-200 bg-neutral-50">
          <tr>
            <th className="px-4 py-3 font-medium text-neutral-600">Title</th>
            <th className="px-4 py-3 font-medium text-neutral-600">Theme</th>
            <th className="px-4 py-3 font-medium text-neutral-600">Pages</th>
            <th className="px-4 py-3 font-medium text-neutral-600">Created</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-neutral-100">
          {ebooks.map((ebook) => (
            <tr
              key={ebook.id}
              className="cursor-pointer hover:bg-neutral-50"
              onClick={() => navigate(`/ebooks/${ebook.id}`)}
            >
              <td className="px-4 py-3 font-medium text-neutral-900">
                {ebook.title}
              </td>
              <td className="px-4 py-3 text-neutral-500">{ebook.theme}</td>
              <td className="px-4 py-3 text-neutral-500">{ebook.num_pages}</td>
              <td className="px-4 py-3 text-neutral-500">
                {ebook.created_at
                  ? new Date(ebook.created_at).toLocaleDateString()
                  : '-'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
