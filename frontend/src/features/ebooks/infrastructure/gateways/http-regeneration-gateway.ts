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
} from '../../domain/ports/regeneration-gateway'
import { authFetch } from '../../../../shared/utils/auth-fetch'

export class HttpRegenerationGateway implements RegenerationGateway {
  private readonly baseUrl = '/api/ebooks'

  async getPageData(ebookId: number, pageIndex: number): Promise<PageData> {
    const res = await authFetch(`${this.baseUrl}/${ebookId}/pages/${pageIndex}/data`)
    if (!res.ok) throw new Error(`Failed to get page data: ${res.status}`)
    return res.json()
  }

  async previewRegenerate(ebookId: number, pageIndex: number, customPrompt?: string, currentImage?: string): Promise<RegenerateResult> {
    const res = await authFetch(`${this.baseUrl}/${ebookId}/pages/${pageIndex}/preview-regenerate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ custom_prompt: customPrompt, current_image_base64: currentImage }),
    })
    if (!res.ok) throw new Error(`Failed to regenerate preview: ${res.status}`)
    return res.json()
  }

  async editPage(ebookId: number, pageIndex: number, editPrompt: string, currentImage?: string): Promise<EditResult> {
    const res = await authFetch(`${this.baseUrl}/${ebookId}/pages/${pageIndex}/edit`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ edit_prompt: editPrompt, current_image_base64: currentImage }),
    })
    if (!res.ok) throw new Error(`Failed to edit page: ${res.status}`)
    return res.json()
  }

  async applyEdit(ebookId: number, pageIndex: number, imageBase64: string, prompt?: string): Promise<ApplyResult> {
    const res = await authFetch(`${this.baseUrl}/${ebookId}/pages/${pageIndex}/apply-edit`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ image_base64: imageBase64, page_index: pageIndex, prompt }),
    })
    if (!res.ok) throw new Error(`Failed to apply edit: ${res.status}`)
    return res.json()
  }

  async previewRegenerateCover(ebookId: number, customPrompt?: string, currentImage?: string): Promise<RegenerateResult> {
    const res = await authFetch(`${this.baseUrl}/${ebookId}/cover/preview-regenerate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ custom_prompt: customPrompt, current_image_base64: currentImage }),
    })
    if (!res.ok) throw new Error(`Failed to regenerate cover: ${res.status}`)
    return res.json()
  }

  async editCover(ebookId: number, editPrompt: string, currentImage?: string): Promise<EditResult> {
    const res = await authFetch(`${this.baseUrl}/${ebookId}/cover/edit`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ edit_prompt: editPrompt, current_image_base64: currentImage }),
    })
    if (!res.ok) throw new Error(`Failed to edit cover: ${res.status}`)
    return res.json()
  }

  async applyCoverEdit(ebookId: number, imageBase64: string, prompt?: string): Promise<ApplyResult> {
    const res = await authFetch(`${this.baseUrl}/${ebookId}/cover/apply-edit`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ image_base64: imageBase64, prompt }),
    })
    if (!res.ok) throw new Error(`Failed to apply cover edit: ${res.status}`)
    return res.json()
  }

  async regenerate(ebookId: number, pageType: PageType, pageIndices?: number[]): Promise<BulkRegenerateResult> {
    const res = await authFetch(`${this.baseUrl}/${ebookId}/regenerate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ page_type: pageType, page_indices: pageIndices }),
    })
    if (!res.ok) throw new Error(`Failed to regenerate: ${res.status}`)
    return res.json()
  }

  async completePages(ebookId: number, targetPages = 24): Promise<CompletePagesResult> {
    const res = await authFetch(`${this.baseUrl}/${ebookId}/complete-pages?target_pages=${targetPages}`, {
      method: 'POST',
    })
    if (!res.ok) throw new Error(`Failed to complete pages: ${res.status}`)
    return res.json()
  }

  async addPages(ebookId: number, count: number): Promise<AddPagesResult> {
    const res = await authFetch(`${this.baseUrl}/${ebookId}/add-pages`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ count }),
    })
    if (!res.ok) throw new Error(`Failed to add pages: ${res.status}`)
    return res.json()
  }
}
