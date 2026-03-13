import type { RootState } from '../../../../app/store'

export const selectEbooks = (state: RootState) => state.ebooks.items
export const selectCurrentEbook = (state: RootState) => state.ebooks.currentEbook
export const selectFormConfig = (state: RootState) => state.ebooks.formConfig
export const selectEbookLoading = (state: RootState) => state.ebooks.loading
export const selectEbookError = (state: RootState) => state.ebooks.error
export const selectPagination = (state: RootState) => state.ebooks.pagination

export const selectProgress = (state: RootState) => state.regeneration.progress
export const selectEditModal = (state: RootState) => state.regeneration.editModal
export const selectPageData = (state: RootState) => state.regeneration.pageData
export const selectPreview = (state: RootState) => state.regeneration.preview
export const selectBulkAction = (state: RootState) => state.regeneration.bulkAction
