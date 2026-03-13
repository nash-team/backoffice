import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { App } from './app/App'
import { createAppStore } from './app/store'
import { HttpEbookGateway } from './features/ebooks/infrastructure/gateways/http-ebook-gateway'
import { HttpExportGateway } from './features/ebooks/infrastructure/gateways/http-export-gateway'
import { HttpRegenerationGateway } from './features/ebooks/infrastructure/gateways/http-regeneration-gateway'
import { ToastContainer } from './shared/components/Toast'
import './shared/styles/theme.css'

const gateways = {
  ebookGateway: new HttpEbookGateway(),
  exportGateway: new HttpExportGateway(),
  regenerationGateway: new HttpRegenerationGateway(),
}

const store = createAppStore(gateways)

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ToastContainer />
    <App store={store} />
  </StrictMode>,
)
