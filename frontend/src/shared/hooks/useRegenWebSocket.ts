import { useEffect, useRef } from 'react'
import { useAppDispatch } from '../../app/hooks'
import { setProgress, clearProgress } from '../../features/ebooks/store/slices/regeneration-slice'
import { getEbookDetail } from '../../features/ebooks/domain/usecases/ebook-usecases'

/**
 * Connects to the backend WebSocket to receive real-time regeneration progress.
 * Dispatches setProgress on each message and refreshes ebook detail when finished.
 */
export function useRegenWebSocket(ebookId: number | undefined) {
  const dispatch = useAppDispatch()
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    if (!ebookId) return

    const clientId = `react-${ebookId}-${Date.now()}`
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}/api/ws/${clientId}`

    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        dispatch(
          setProgress({
            ebookId: data.ebook_id,
            pageIndex: data.page_index,
            currentStep: Number(data.current_step) || 0,
            status: Number(data.status) || 0,
            state: data.state === 'finished' ? 'finished' : 'running',
          }),
        )

        if (data.state === 'finished') {
          dispatch(getEbookDetail(ebookId))
          setTimeout(() => dispatch(clearProgress()), 2000)
        }
      } catch {
        // ignore malformed messages
      }
    }

    ws.onerror = (event) => {
      console.warn('WebSocket error:', event)
    }

    return () => {
      wsRef.current = null
      if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
        ws.close()
      }
    }
  }, [ebookId, dispatch])
}
