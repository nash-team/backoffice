export interface PageData {
  success: boolean
  ebook_id: number
  page_index: number
  image_base64: string
  prompt: string
  title: string
}

export interface RegenerateResult {
  success: boolean
  image_base64: string
  page_index: number
  prompt_used: string
}

export interface EditResult {
  success: boolean
  image_base64: string
  page_index: number
  edit_prompt_used: string
}

export interface ApplyResult {
  success: boolean
  message: string
  ebook_id: number
  preview_url: string
}

export type PageType = 'cover' | 'back_cover' | 'content_page'

export interface BulkRegenerateResult {
  success: boolean
  message: string
  ebook_id: number
  preview_url: string
}

export interface CompletePagesResult {
  success: boolean
  message: string
  page_count: number
}

export interface AddPagesResult {
  success: boolean
  message: string
  pages_added: number
  total_pages: number
  limit_reached: boolean
}

export interface RegenerationGateway {
  getPageData(ebookId: number, pageIndex: number): Promise<PageData>
  previewRegenerate(ebookId: number, pageIndex: number, customPrompt?: string, currentImage?: string): Promise<RegenerateResult>
  editPage(ebookId: number, pageIndex: number, editPrompt: string, currentImage?: string): Promise<EditResult>
  applyEdit(ebookId: number, pageIndex: number, imageBase64: string, prompt?: string): Promise<ApplyResult>
  previewRegenerateCover(ebookId: number, customPrompt?: string, currentImage?: string): Promise<RegenerateResult>
  editCover(ebookId: number, editPrompt: string, currentImage?: string): Promise<EditResult>
  applyCoverEdit(ebookId: number, imageBase64: string, prompt?: string): Promise<ApplyResult>
  regenerate(ebookId: number, pageType: PageType, pageIndices?: number[]): Promise<BulkRegenerateResult>
  completePages(ebookId: number, targetPages?: number): Promise<CompletePagesResult>
  addPages(ebookId: number, count: number): Promise<AddPagesResult>
}
