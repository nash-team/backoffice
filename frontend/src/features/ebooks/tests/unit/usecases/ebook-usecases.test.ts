import { describe, it, expect, beforeEach } from 'vitest'
import { createAppStore } from '../../../../../app/store'
import type { AppStore } from '../../../../../app/store'
import { FakeEbookGateway } from '../../../../../tests/fakes/fake-ebook-gateway'
import { FakeExportGateway } from '../../../../../tests/fakes/fake-export-gateway'
import { FakeRegenerationGateway } from '../../../../../tests/fakes/fake-regeneration-gateway'
import type { Ebook } from '../../../domain/entities/ebook'
import {
  listEbooks,
  getEbookDetail,
  createEbook,
  fetchFormConfig,
} from '../../../domain/usecases/ebook-usecases'

const SAMPLE_EBOOK: Ebook = {
  id: 1,
  title: 'Dinosaurs Coloring Book',
  theme: 'dinosaurs',
  audience: 'children',
  num_pages: 24,
  created_at: '2026-01-15T10:00:00',
  updated_at: '2026-01-15T10:00:00',
}

const SECOND_EBOOK: Ebook = {
  id: 2,
  title: 'Pirates Coloring Book',
  theme: 'pirates',
  audience: 'adults',
  num_pages: 30,
  created_at: '2026-01-16T10:00:00',
  updated_at: '2026-01-16T10:00:00',
}

describe('Ebook use cases (Chicago-style with fakes)', () => {
  let store: AppStore
  let fakeGateway: FakeEbookGateway

  beforeEach(() => {
    fakeGateway = new FakeEbookGateway([SAMPLE_EBOOK, SECOND_EBOOK])
    store = createAppStore({
      ebookGateway: fakeGateway,
      exportGateway: new FakeExportGateway(),
      regenerationGateway: new FakeRegenerationGateway(),
    })
  })

  describe('listEbooks', () => {
    it('loads ebooks into the store', async () => {
      await store.dispatch(listEbooks({ page: 1 }))

      const state = store.getState().ebooks
      expect(state.items).toHaveLength(2)
      expect(state.items[0].title).toBe('Dinosaurs Coloring Book')
      expect(state.pagination.total).toBe(2)
      expect(state.loading).toBe(false)
      expect(fakeGateway.callCounts.list).toBe(1)
    })

    it('sets loading while pending', () => {
      store.dispatch(listEbooks({ page: 1 }))
      expect(store.getState().ebooks.loading).toBe(true)
    })
  })

  describe('getEbookDetail', () => {
    it('loads a single ebook into currentEbook', async () => {
      await store.dispatch(getEbookDetail(1))

      const state = store.getState().ebooks
      expect(state.currentEbook).not.toBeNull()
      expect(state.currentEbook!.id).toBe(1)
      expect(fakeGateway.callCounts.getById).toBe(1)
    })

    it('sets error when ebook not found', async () => {
      await store.dispatch(getEbookDetail(999))

      const state = store.getState().ebooks
      expect(state.error).toContain('999')
      expect(state.currentEbook).toBeNull()
    })
  })

  describe('createEbook', () => {
    it('adds new ebook to the store', async () => {
      await store.dispatch(
        createEbook({
          theme: 'unicorns',
          audience: 'children',
          num_pages: 8,
        }),
      )

      const state = store.getState().ebooks
      expect(state.items[0].title).toBe('unicorns Coloring Book')
      expect(state.pagination.total).toBe(1)
      expect(fakeGateway.callCounts.create).toBe(1)
    })
  })

  describe('fetchFormConfig', () => {
    it('loads form config into the store', async () => {
      await store.dispatch(fetchFormConfig())

      const state = store.getState().ebooks
      expect(state.formConfig).not.toBeNull()
      expect(state.formConfig!.themes).toContain('dinosaurs')
      expect(state.formConfig!.audiences).toContain('children')
      expect(fakeGateway.callCounts.getFormConfig).toBe(1)
    })
  })
})
