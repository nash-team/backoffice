import { describe, it, expect } from 'vitest'
import type { RootState } from '../../../../../app/store'
import {
  selectEbooks,
  selectCurrentEbook,
  selectPagination,
  selectEbookLoading,
  selectEbookError,
  selectProgress,
  selectEditModal,
} from '../../../store/selectors/ebook-selectors'

function buildState(overrides: {
  ebooks?: Partial<RootState['ebooks']>
  regeneration?: Partial<RootState['regeneration']>
} = {}): RootState {
  return {
    ebooks: {
      items: [],
      currentEbook: null,
      formConfig: null,
      pagination: { page: 1, totalPages: 0, total: 0, perPage: 15 },
      loading: false,
      error: null,
      ...overrides.ebooks,
    },
    regeneration: {
      bulkAction: { loading: false, error: null },
      progress: null,
      editModal: { open: false, ebookId: null, pageIndex: null, isCover: false },
      pageData: { imageBase64: null, prompt: null, title: null, loading: false },
      preview: { imageBase64: null, loading: false },
      ...overrides.regeneration,
    },
  }
}

describe('Ebook selectors', () => {
  it('selectEbooks returns items', () => {
    const ebook = { id: 1, title: 'Test', theme: 't', audience: 'a', num_pages: 8, created_at: '', updated_at: '' }
    const state = buildState({ ebooks: { items: [ebook] } })
    expect(selectEbooks(state)).toEqual([ebook])
  })

  it('selectCurrentEbook returns current ebook', () => {
    const ebook = { id: 1, title: 'Test', theme: 't', audience: 'a', num_pages: 8, created_at: '', updated_at: '' }
    const state = buildState({ ebooks: { currentEbook: ebook } })
    expect(selectCurrentEbook(state)).toEqual(ebook)
  })

  it('selectPagination returns pagination info', () => {
    const pagination = { page: 2, totalPages: 5, total: 73, perPage: 15 }
    const state = buildState({ ebooks: { pagination } })
    expect(selectPagination(state)).toEqual(pagination)
  })

  it('selectEbookLoading returns loading state', () => {
    const state = buildState({ ebooks: { loading: true } })
    expect(selectEbookLoading(state)).toBe(true)
  })

  it('selectEbookError returns error', () => {
    const state = buildState({ ebooks: { error: 'Something went wrong' } })
    expect(selectEbookError(state)).toBe('Something went wrong')
  })

  it('selectProgress returns regeneration progress', () => {
    const progress = { ebookId: 1, pageIndex: 3, currentStep: 'generating', status: '50%', state: 'running' as const }
    const state = buildState({ regeneration: { progress } })
    expect(selectProgress(state)).toEqual(progress)
  })

  it('selectEditModal returns modal state', () => {
    const modal = { open: true, ebookId: 1, pageIndex: 2, isCover: false }
    const state = buildState({ regeneration: { editModal: modal } })
    expect(selectEditModal(state)).toEqual(modal)
  })
})
