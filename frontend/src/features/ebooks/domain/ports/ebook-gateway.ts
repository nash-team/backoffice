import type { Ebook, PaginatedResult, FormConfig } from '../entities/ebook'

export interface EbookGateway {
  list(page: number): Promise<PaginatedResult<Ebook>>
  getById(id: number): Promise<Ebook>
  create(data: CreateEbookRequest): Promise<Ebook>
  getFormConfig(): Promise<FormConfig>
}

export interface CreateEbookRequest {
  theme: string
  audience: string
  num_pages: number
  preview_mode?: boolean
}
