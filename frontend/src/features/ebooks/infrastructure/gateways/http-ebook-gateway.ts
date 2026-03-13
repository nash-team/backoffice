import type { Ebook, FormConfig, PaginatedResult } from '../../domain/entities/ebook'
import type { CreateEbookRequest, EbookGateway } from '../../domain/ports/ebook-gateway'

export class HttpEbookGateway implements EbookGateway {
  private readonly baseUrl = '/api'

  async list(page: number): Promise<PaginatedResult<Ebook>> {
    const params = new URLSearchParams({ page: String(page) })
    const res = await fetch(`${this.baseUrl}/ebooks?${params}`, { credentials: 'include' })
    if (!res.ok) throw new Error(`Failed to list ebooks: ${res.status}`)
    return res.json()
  }

  async getById(id: number): Promise<Ebook> {
    const res = await fetch(`${this.baseUrl}/ebooks/${id}`, { credentials: 'include' })
    if (!res.ok) throw new Error(`Failed to get ebook: ${res.status}`)
    return res.json()
  }

  async create(data: CreateEbookRequest): Promise<Ebook> {
    const res = await fetch(`${this.baseUrl}/ebooks`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
    if (!res.ok) throw new Error(`Failed to create ebook: ${res.status}`)
    return res.json()
  }

  async getFormConfig(): Promise<FormConfig> {
    const res = await fetch(`${this.baseUrl}/ebooks/form-config`, { credentials: 'include' })
    if (!res.ok) throw new Error(`Failed to get form config: ${res.status}`)
    return res.json()
  }
}
