import { createBrowserRouter } from 'react-router-dom'
import { AppLayout } from '../shared/components/AppLayout'
import { DashboardPage } from '../features/ebooks/presentation/pages/DashboardPage'
import { EbookDetailPage } from '../features/ebooks/presentation/pages/EbookDetailPage'

export const router = createBrowserRouter([
  {
    element: <AppLayout />,
    children: [
      { path: '/', element: <DashboardPage /> },
      { path: '/ebooks/:id', element: <EbookDetailPage /> },
    ],
  },
])
