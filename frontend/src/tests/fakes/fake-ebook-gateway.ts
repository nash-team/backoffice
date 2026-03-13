import type { Ebook, FormConfig, PaginatedResult } from '../../features/ebooks/domain/entities/ebook'
import type { CreateEbookRequest, EbookGateway } from '../../features/ebooks/domain/ports/ebook-gateway'

export class FakeEbookGateway implements EbookGateway {
  private ebooks: Ebook[] = []
  private nextId = 1
  public callCounts = { list: 0, getById: 0, create: 0, getFormConfig: 0 }

  constructor(initialEbooks: Ebook[] = []) {
    this.ebooks = [...initialEbooks]
    if (initialEbooks.length > 0) {
      this.nextId = Math.max(...initialEbooks.map((e) => e.id)) + 1
    }
  }

  async list(page: number): Promise<PaginatedResult<Ebook>> {
    this.callCounts.list++
    const perPage = 15
    const start = (page - 1) * perPage
    const items = this.ebooks.slice(start, start + perPage)
    return {
      items,
      total: this.ebooks.length,
      page,
      per_page: perPage,
      total_pages: Math.ceil(this.ebooks.length / perPage),
    }
  }

  async getById(id: number): Promise<Ebook> {
    this.callCounts.getById++
    const ebook = this.ebooks.find((e) => e.id === id)
    if (!ebook) throw new Error(`Ebook ${id} not found`)
    return ebook
  }

  async create(data: CreateEbookRequest): Promise<Ebook> {
    this.callCounts.create++
    const ebook: Ebook = {
      id: this.nextId++,
      title: `${data.theme} Coloring Book`,
      theme: data.theme,
      audience: data.audience,
      num_pages: data.num_pages,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }
    this.ebooks.unshift(ebook)
    return ebook
  }

  async getFormConfig(): Promise<FormConfig> {
    this.callCounts.getFormConfig++
    return {
      themes: ['dinosaurs', 'unicorns', 'pirates'],
      audiences: ['children', 'adults'],
    }
  }
}
