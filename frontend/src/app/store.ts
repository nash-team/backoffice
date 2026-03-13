import { configureStore, createListenerMiddleware } from '@reduxjs/toolkit'
import type { Gateways } from '../features/ebooks/domain/ports/gateways'
import { ebookSlice } from '../features/ebooks/store/slices/ebook-slice'
import { regenerationSlice } from '../features/ebooks/store/slices/regeneration-slice'

export const listenerMiddleware = createListenerMiddleware()

export function createAppStore(gateways: Gateways) {
  return configureStore({
    reducer: {
      ebooks: ebookSlice.reducer,
      regeneration: regenerationSlice.reducer,
    },
    middleware: (getDefaultMiddleware) =>
      getDefaultMiddleware({
        thunk: { extraArgument: gateways },
      }).prepend(listenerMiddleware.middleware),
  })
}

export type AppStore = ReturnType<typeof createAppStore>
export type RootState = ReturnType<AppStore['getState']>
export type AppDispatch = AppStore['dispatch']
