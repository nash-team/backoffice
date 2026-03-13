import { createBrowserRouter } from 'react-router-dom'
import { AppLayout } from '../shared/components/AppLayout'
import { DashboardPage } from '../features/ebooks/presentation/pages/DashboardPage'
import { EbookDetailPage } from '../features/ebooks/presentation/pages/EbookDetailPage'
import { LoginPage } from '../features/auth/presentation/pages/LoginPage'

export const router = createBrowserRouter([
  { path: '/login', element: <LoginPage /> },
  {
    element: <AppLayout />,
    children: [
      { path: '/', element: <DashboardPage /> },
      { path: '/ebooks/:id', element: <EbookDetailPage /> },
    ],
  },
])
