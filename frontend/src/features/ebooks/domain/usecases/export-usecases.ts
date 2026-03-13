import { createAsyncThunk } from '@reduxjs/toolkit'
import type { Gateways } from '../ports/gateways'

export type ExportType = 'pdf' | 'kdp-interior' | 'kdp-cover' | 'kdp-full'

export const exportEbook = createAsyncThunk(
  'export/exportEbook',
  async ({ ebookId, type }: { ebookId: number; type: ExportType }, { extra }) => {
    const { exportGateway } = extra as Gateways
    const exportFns = {
      'pdf': () => exportGateway.downloadPdf(ebookId),
      'kdp-interior': () => exportGateway.exportKdpInterior(ebookId),
      'kdp-cover': () => exportGateway.exportKdpCover(ebookId),
      'kdp-full': () => exportGateway.exportKdpFull(ebookId),
    } as const
    const blob = await exportFns[type]()
    return { blob, type }
  },
)

export const fetchKdpCoverPreview = createAsyncThunk(
  'export/fetchKdpCoverPreview',
  async (ebookId: number, { extra }) => {
    const { exportGateway } = extra as Gateways
    return exportGateway.exportKdpCover(ebookId)
  },
)

export const fetchPageImage = createAsyncThunk(
  'regeneration/fetchPageImage',
  async ({ ebookId, pageIndex }: { ebookId: number; pageIndex: number }, { extra }) => {
    const { regenerationGateway } = extra as Gateways
    const data = await regenerationGateway.getPageData(ebookId, pageIndex)
    return { pageIndex, imageBase64: data.image_base64 }
  },
)
