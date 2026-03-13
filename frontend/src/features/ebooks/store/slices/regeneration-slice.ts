import { createSlice, type PayloadAction } from '@reduxjs/toolkit'
import { fetchPageData, previewRegenerate, editPage, previewRegenerateCover, editCover, regeneratePages, completePages, addNewPages } from '../../domain/usecases/regeneration-usecases'

export interface RegenerationProgress {
  ebookId: number
  pageIndex: number
  currentStep: number
  status: number
  state: 'running' | 'finished'
}

export interface RegenerationState {
  bulkAction: { loading: boolean; error: string | null }
  progress: RegenerationProgress | null
  editModal: {
    open: boolean
    ebookId: number | null
    pageIndex: number | null
    isCover: boolean
  }
  pageData: {
    imageBase64: string | null
    prompt: string | null
    title: string | null
    loading: boolean
  }
  preview: {
    imageBase64: string | null
    loading: boolean
  }
}

const initialState: RegenerationState = {
  bulkAction: { loading: false, error: null },
  progress: null,
  editModal: {
    open: false,
    ebookId: null,
    pageIndex: null,
    isCover: false,
  },
  pageData: {
    imageBase64: null,
    prompt: null,
    title: null,
    loading: false,
  },
  preview: {
    imageBase64: null,
    loading: false,
  },
}

export const regenerationSlice = createSlice({
  name: 'regeneration',
  initialState,
  reducers: {
    setProgress(state, action: PayloadAction<RegenerationProgress>) {
      state.progress = action.payload
    },
    clearProgress(state) {
      state.progress = null
    },
    openEditModal(state, action: PayloadAction<{ ebookId: number; pageIndex: number; isCover?: boolean }>) {
      state.editModal = {
        open: true,
        ebookId: action.payload.ebookId,
        pageIndex: action.payload.pageIndex,
        isCover: action.payload.isCover ?? false,
      }
      state.pageData = { imageBase64: null, prompt: null, title: null, loading: false }
      state.preview = { imageBase64: null, loading: false }
    },
    closeEditModal(state) {
      state.editModal = { open: false, ebookId: null, pageIndex: null, isCover: false }
      state.pageData = { imageBase64: null, prompt: null, title: null, loading: false }
      state.preview = { imageBase64: null, loading: false }
    },
    restorePreview(state, action: PayloadAction<string>) {
      state.preview = { imageBase64: action.payload, loading: false }
    },
  },
  extraReducers: (builder) => {
    // fetchPageData
    builder
      .addCase(fetchPageData.pending, (state) => {
        state.pageData.loading = true
      })
      .addCase(fetchPageData.fulfilled, (state, action) => {
        state.pageData = {
          imageBase64: action.payload.image_base64,
          prompt: action.payload.prompt,
          title: action.payload.title,
          loading: false,
        }
      })
      .addCase(fetchPageData.rejected, (state) => {
        state.pageData.loading = false
      })

    // previewRegenerate
    builder
      .addCase(previewRegenerate.pending, (state) => {
        state.preview.loading = true
      })
      .addCase(previewRegenerate.fulfilled, (state, action) => {
        state.preview = { imageBase64: action.payload.image_base64, loading: false }
      })
      .addCase(previewRegenerate.rejected, (state) => {
        state.preview.loading = false
      })

    // editPage
    builder
      .addCase(editPage.pending, (state) => {
        state.preview.loading = true
      })
      .addCase(editPage.fulfilled, (state, action) => {
        state.preview = { imageBase64: action.payload.image_base64, loading: false }
      })
      .addCase(editPage.rejected, (state) => {
        state.preview.loading = false
      })

    // previewRegenerateCover
    builder
      .addCase(previewRegenerateCover.pending, (state) => {
        state.preview.loading = true
      })
      .addCase(previewRegenerateCover.fulfilled, (state, action) => {
        state.preview = { imageBase64: action.payload.image_base64, loading: false }
      })
      .addCase(previewRegenerateCover.rejected, (state) => {
        state.preview.loading = false
      })

    // editCover
    builder
      .addCase(editCover.pending, (state) => {
        state.preview.loading = true
      })
      .addCase(editCover.fulfilled, (state, action) => {
        state.preview = { imageBase64: action.payload.image_base64, loading: false }
      })
      .addCase(editCover.rejected, (state) => {
        state.preview.loading = false
      })

    // bulk actions
    for (const thunk of [regeneratePages, completePages, addNewPages]) {
      builder
        .addCase(thunk.pending, (state) => {
          state.bulkAction = { loading: true, error: null }
        })
        .addCase(thunk.fulfilled, (state) => {
          state.bulkAction = { loading: false, error: null }
        })
        .addCase(thunk.rejected, (state, action) => {
          state.bulkAction = { loading: false, error: action.error.message ?? 'Unknown error' }
        })
    }
  },
})

export const { setProgress, clearProgress, openEditModal, closeEditModal, restorePreview } =
  regenerationSlice.actions
