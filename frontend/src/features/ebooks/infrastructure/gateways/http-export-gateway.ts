import type { ExportGateway } from '../../domain/ports/export-gateway'
import { authFetch } from '../../../../shared/utils/auth-fetch'

export class HttpExportGateway implements ExportGateway {
  private readonly baseUrl = '/api/ebooks'

  async downloadPdf(ebookId: number): Promise<Blob> {
    const res = await authFetch(`${this.baseUrl}/${ebookId}/pdf`)
    if (!res.ok) throw new Error(`Failed to download PDF: ${res.status}`)
    return res.blob()
  }

  async exportKdpInterior(ebookId: number): Promise<Blob> {
    const res = await authFetch(`${this.baseUrl}/${ebookId}/export-kdp/interior`)
    if (!res.ok) throw new Error(`Failed to export KDP interior: ${res.status}`)
    return res.blob()
  }

  async exportKdpCover(ebookId: number): Promise<Blob> {
    const res = await authFetch(`${this.baseUrl}/${ebookId}/kdp-cover-preview`)
    if (!res.ok) throw new Error(`Failed to export KDP cover: ${res.status}`)
    return res.blob()
  }

  async exportKdpFull(ebookId: number): Promise<Blob> {
    const res = await authFetch(`${this.baseUrl}/${ebookId}/export-kdp`)
    if (!res.ok) throw new Error(`Failed to export KDP full: ${res.status}`)
    return res.blob()
  }
}
