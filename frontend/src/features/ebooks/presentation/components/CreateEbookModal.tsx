import { useEffect, useState } from 'react'
import { useAppDispatch, useAppSelector } from '../../../../app/hooks'
import { Modal } from '../../../../shared/components/Modal'
import { showToast } from '../../../../shared/components/Toast'
import type { ThemeOption, AudienceOption } from '../../domain/entities/ebook'
import { selectFormConfig } from '../../store/selectors/ebook-selectors'
import {
  createEbook,
  fetchFormConfig,
  listEbooks,
} from '../../domain/usecases/ebook-usecases'

interface CreateEbookModalProps {
  open: boolean
  onClose: () => void
}

function optionId(o: string | ThemeOption | AudienceOption): string {
  return typeof o === 'string' ? o : o.id
}

function optionLabel(o: string | ThemeOption | AudienceOption): string {
  return typeof o === 'string' ? o : ('label' in o && o.label ? o.label : o.id)
}

export function CreateEbookModal({ open, onClose }: CreateEbookModalProps) {
  const dispatch = useAppDispatch()
  const formConfig = useAppSelector(selectFormConfig)
  const [submitting, setSubmitting] = useState(false)

  const [form, setForm] = useState({
    theme: '',
    audience: '',
    num_pages: 8,
    preview_mode: false,
  })

  useEffect(() => {
    if (open && !formConfig) {
      dispatch(fetchFormConfig())
    }
  }, [open, formConfig, dispatch])

  useEffect(() => {
    if (formConfig && !form.theme && formConfig.themes.length > 0) {
      setForm((f) => ({
        ...f,
        theme: optionId(formConfig.themes[0]),
        audience: optionId(formConfig.audiences[0]),
      }))
    }
  }, [formConfig, form.theme])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setSubmitting(true)
    try {
      await dispatch(
        createEbook({
          theme: form.theme,
          audience: form.audience,
          num_pages: form.num_pages,
          preview_mode: form.preview_mode,
        }),
      ).unwrap()
      showToast('success', 'Ebook creation started')
      dispatch(listEbooks({ page: 1 }))
      onClose()
      setForm({ theme: '', audience: '', num_pages: 8, preview_mode: false })
    } catch {
      showToast('error', 'Failed to create ebook')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Modal open={open} onClose={onClose} title="Create New Ebook">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="mb-1 block text-sm font-medium text-neutral-700">
            Theme
          </label>
          <select
            value={form.theme}
            onChange={(e) => setForm({ ...form, theme: e.target.value })}
            required
            className="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
          >
            <option value="">Select a theme...</option>
            {formConfig?.themes.map((t) => (
              <option key={optionId(t)} value={optionId(t)}>
                {optionLabel(t)}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium text-neutral-700">
            Audience
          </label>
          <select
            value={form.audience}
            onChange={(e) => setForm({ ...form, audience: e.target.value })}
            required
            className="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
          >
            <option value="">Select audience...</option>
            {formConfig?.audiences.map((a) => (
              <option key={optionId(a)} value={optionId(a)}>
                {optionLabel(a)}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium text-neutral-700">
            Number of pages
          </label>
          <input
            type="number"
            min={1}
            max={100}
            value={form.num_pages}
            onChange={(e) =>
              setForm({ ...form, num_pages: parseInt(e.target.value) || 8 })
            }
            disabled={form.preview_mode}
            className="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500 disabled:bg-neutral-100 disabled:text-neutral-400"
          />
          {form.preview_mode && (
            <p className="mt-1 text-xs text-neutral-500">Preview generates 1 page only</p>
          )}
        </div>

        <div className="flex items-center gap-2">
          <input
            type="checkbox"
            id="preview_mode"
            checked={form.preview_mode}
            onChange={(e) =>
              setForm({ ...form, preview_mode: e.target.checked, num_pages: e.target.checked ? 1 : 8 })
            }
            className="h-4 w-4 rounded border-neutral-300 text-primary-600 focus:ring-primary-500"
          />
          <label htmlFor="preview_mode" className="text-sm font-medium text-neutral-700">
            Preview mode
          </label>
          <span className="text-xs text-neutral-500">(fast, 1 page only)</span>
        </div>

        <div className="flex justify-end gap-3 pt-2">
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border border-neutral-300 px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={submitting || !form.theme || !form.audience}
            className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
          >
            {submitting ? 'Creating...' : form.preview_mode ? 'Preview' : 'Create Ebook'}
          </button>
        </div>
      </form>
    </Modal>
  )
}
