import type {
  AddPagesResult,
  ApplyResult,
  BulkRegenerateResult,
  CompletePagesResult,
  EditResult,
  PageData,
  PageType,
  RegenerateResult,
  RegenerationGateway,
} from '../../features/ebooks/domain/ports/regeneration-gateway'

export class FakeRegenerationGateway implements RegenerationGateway {
  public callCounts = {
    getPageData: 0, previewRegenerate: 0, editPage: 0, applyEdit: 0,
    previewRegenerateCover: 0, editCover: 0, applyCoverEdit: 0,
    regenerate: 0, completePages: 0, addPages: 0,
  }

  async getPageData(ebookId: number, pageIndex: number): Promise<PageData> {
    this.callCounts.getPageData++
    return { success: true, ebook_id: ebookId, page_index: pageIndex, image_base64: 'fake-base64', prompt: 'a dinosaur', title: `Page ${pageIndex}` }
  }

  async previewRegenerate(_ebookId: number, pageIndex: number): Promise<RegenerateResult> {
    this.callCounts.previewRegenerate++
    return { success: true, image_base64: 'regenerated-base64', page_index: pageIndex, prompt_used: 'regen prompt' }
  }

  async editPage(_ebookId: number, pageIndex: number): Promise<EditResult> {
    this.callCounts.editPage++
    return { success: true, image_base64: 'edited-base64', page_index: pageIndex, edit_prompt_used: 'edit prompt' }
  }

  async applyEdit(ebookId: number, _pageIndex: number): Promise<ApplyResult> {
    this.callCounts.applyEdit++
    return { success: true, message: 'Applied', ebook_id: ebookId, preview_url: '/preview' }
  }

  async previewRegenerateCover(_ebookId: number): Promise<RegenerateResult> {
    this.callCounts.previewRegenerateCover++
    return { success: true, image_base64: 'cover-regen-base64', page_index: 0, prompt_used: 'cover prompt' }
  }

  async editCover(_ebookId: number): Promise<EditResult> {
    this.callCounts.editCover++
    return { success: true, image_base64: 'cover-edited-base64', page_index: 0, edit_prompt_used: 'cover edit' }
  }

  async applyCoverEdit(ebookId: number): Promise<ApplyResult> {
    this.callCounts.applyCoverEdit++
    return { success: true, message: 'Cover applied', ebook_id: ebookId, preview_url: '/cover-preview' }
  }

  async regenerate(ebookId: number, _pageType: PageType, _pageIndices?: number[]): Promise<BulkRegenerateResult> {
    this.callCounts.regenerate++
    return { success: true, message: 'Regenerated', ebook_id: ebookId, preview_url: '/preview' }
  }

  async completePages(_ebookId: number, _targetPages?: number): Promise<CompletePagesResult> {
    this.callCounts.completePages++
    return { success: true, message: 'Completed to 24 pages', page_count: 24 }
  }

  async addPages(ebookId: number, count: number): Promise<AddPagesResult> {
    this.callCounts.addPages++
    return { success: true, message: `Added ${count} pages`, pages_added: count, total_pages: 10 + count, limit_reached: false }
  }
}
