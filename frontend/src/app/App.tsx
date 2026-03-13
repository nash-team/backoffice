import { Provider } from 'react-redux'
import { RouterProvider } from 'react-router-dom'
import { router } from './router'
import type { AppStore } from './store'

interface AppProps {
  store: AppStore
}

export function App({ store }: AppProps) {
  return (
    <Provider store={store}>
      <RouterProvider router={router} />
    </Provider>
  )
}
