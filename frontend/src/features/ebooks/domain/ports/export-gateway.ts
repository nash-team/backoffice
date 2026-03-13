export interface ExportGateway {
  downloadPdf(ebookId: number): Promise<Blob>
  exportKdpInterior(ebookId: number): Promise<Blob>
  exportKdpCover(ebookId: number): Promise<Blob>
  exportKdpFull(ebookId: number): Promise<Blob>
}
