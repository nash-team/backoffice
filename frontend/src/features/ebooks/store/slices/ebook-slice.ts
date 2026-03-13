import { createSlice } from '@reduxjs/toolkit'
import type { Ebook, FormConfig } from '../../domain/entities/ebook'
import {
  listEbooks,
  getEbookDetail,
  createEbook,
  fetchFormConfig,
} from '../../domain/usecases/ebook-usecases'

export interface EbookState {
  items: Ebook[]
  currentEbook: Ebook | null
  formConfig: FormConfig | null
  pagination: {
    page: number
    totalPages: number
    total: number
    perPage: number
  }
  loading: boolean
  error: string | null
}

const initialState: EbookState = {
  items: [],
  currentEbook: null,
  formConfig: null,
  pagination: {
    page: 1,
    totalPages: 0,
    total: 0,
    perPage: 15,
  },
  loading: false,
  error: null,
}

export const ebookSlice = createSlice({
  name: 'ebooks',
  initialState,
  reducers: {
    setPage(state, action: { payload: number }) {
      state.pagination.page = action.payload
    },
    clearCurrentEbook(state) {
      state.currentEbook = null
    },
  },
  extraReducers: (builder) => {
    // listEbooks
    builder
      .addCase(listEbooks.pending, (state) => {
        state.loading = true
        state.error = null
      })
      .addCase(listEbooks.fulfilled, (state, action) => {
        state.loading = false
        state.items = action.payload.items
        state.pagination = {
          page: action.payload.page,
          totalPages: action.payload.total_pages,
          total: action.payload.total,
          perPage: action.payload.per_page,
        }
      })
      .addCase(listEbooks.rejected, (state, action) => {
        state.loading = false
        state.error = action.error.message ?? 'Failed to load ebooks'
      })

    // getEbookDetail
    builder
      .addCase(getEbookDetail.pending, (state) => {
        state.loading = true
        state.error = null
      })
      .addCase(getEbookDetail.fulfilled, (state, action) => {
        state.loading = false
        state.currentEbook = action.payload
      })
      .addCase(getEbookDetail.rejected, (state, action) => {
        state.loading = false
        state.error = action.error.message ?? 'Failed to load ebook'
      })

    // createEbook
    builder.addCase(createEbook.fulfilled, (state, action) => {
      state.items.unshift(action.payload)
      state.pagination.total += 1
    })

    // fetchFormConfig
    builder.addCase(fetchFormConfig.fulfilled, (state, action) => {
      state.formConfig = action.payload
    })
  },
})

export const { setPage, clearCurrentEbook } = ebookSlice.actions
