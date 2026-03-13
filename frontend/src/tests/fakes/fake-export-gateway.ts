import type { ExportGateway } from '../../features/ebooks/domain/ports/export-gateway'

export class FakeExportGateway implements ExportGateway {
  public callCounts = { downloadPdf: 0, exportKdpInterior: 0, exportKdpCover: 0, exportKdpFull: 0 }

  async downloadPdf(_ebookId: number): Promise<Blob> {
    this.callCounts.downloadPdf++
    return new Blob(['fake-pdf'], { type: 'application/pdf' })
  }

  async exportKdpInterior(_ebookId: number): Promise<Blob> {
    this.callCounts.exportKdpInterior++
    return new Blob(['fake-interior'], { type: 'application/pdf' })
  }

  async exportKdpCover(_ebookId: number): Promise<Blob> {
    this.callCounts.exportKdpCover++
    return new Blob(['fake-cover'], { type: 'application/pdf' })
  }

  async exportKdpFull(_ebookId: number): Promise<Blob> {
    this.callCounts.exportKdpFull++
    return new Blob(['fake-full'], { type: 'application/pdf' })
  }
}
