import type { EbookGateway } from './ebook-gateway'
import type { ExportGateway } from './export-gateway'
import type { RegenerationGateway } from './regeneration-gateway'

export interface Gateways {
  readonly ebookGateway: EbookGateway
  readonly exportGateway: ExportGateway
  readonly regenerationGateway: RegenerationGateway
}
