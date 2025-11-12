import { useEffect, useRef, useCallback, useState } from 'react'

// Returns { wsRef, status } and manages reconnection with exponential backoff
export function useWebSocket(deviceIds, onMessage) {
  const wsRef = useRef(null)
  const reconnectTimeoutRef = useRef(null)
  const backoffRef = useRef(1000) // start at 1s
  const lastDevicesRef = useRef('')
  const [status, setStatus] = useState('idle') // idle | connecting | open | error | closed
  const DEBUG = (typeof import.meta !== 'undefined' && import.meta.env && (import.meta.env.DEV || import.meta.env.VITE_WS_DEBUG === 'true'))

  const connect = useCallback(() => {
    if (!deviceIds || deviceIds.length === 0) {
      return
    }
    setStatus('connecting')
    // Prefer configured WS base (e.g., ws://localhost:8001), otherwise derive sensible default
    const envWsBase = (typeof import.meta !== 'undefined' && import.meta.env && import.meta.env.VITE_WS_BASE) || null
    const isHttps = window.location.protocol === 'https:'
    const defaultWsBase = isHttps ? 'wss://localhost:8001' : 'ws://localhost:8001'
    const sameHostWsBase = `${isHttps ? 'wss:' : 'ws:'}//${window.location.host}`
    const wsBase = envWsBase || (window.location.hostname === 'localhost' ? defaultWsBase : sameHostWsBase)
    const devicesStr = deviceIds.join(',')
    const wsUrl = `${wsBase}/ws/tracker?devices=${devicesStr}`

    // Avoid redundant reconnects if already open for the same devices
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN && lastDevicesRef.current === devicesStr) {
      return
    }

    // If a socket exists but not suitable, close it before opening a new one
    if (wsRef.current) {
      try { wsRef.current.onclose = null; wsRef.current.close() } catch {}
    }

    if (DEBUG) console.log('[WebSocket] Connecting:', wsUrl)
    wsRef.current = new WebSocket(wsUrl)
    lastDevicesRef.current = devicesStr

    wsRef.current.onopen = () => {
      if (DEBUG) console.log('[WebSocket] Connected')
      setStatus('open')
      backoffRef.current = 1000 // reset backoff
    }

    wsRef.current.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data)
        onMessage && onMessage(msg)
      } catch (err) {
        if (DEBUG) console.warn('[WebSocket] Parse error:', err)
      }
    }

    wsRef.current.onerror = (err) => {
      if (DEBUG) console.error('[WebSocket] Error:', err)
      setStatus('error')
    }

    wsRef.current.onclose = () => {
      if (DEBUG) console.log('[WebSocket] Closed, scheduling reconnect...')
      setStatus('closed')
      // Exponential backoff with max 30s
      const delay = Math.min(backoffRef.current, 30000)
      backoffRef.current = Math.min(backoffRef.current * 2, 30000)
      reconnectTimeoutRef.current = setTimeout(() => {
        connect()
      }, delay)
    }
  }, [deviceIds, onMessage, DEBUG])

  useEffect(() => {
    if (deviceIds.length > 0) {
      connect()
    }
  }, [connect, deviceIds])

  // Unmount cleanup only
  useEffect(() => {
    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
      if (wsRef.current) {
        try { wsRef.current.close() } catch {}
      }
    }
  }, [])

  return { wsRef: wsRef.current, status }
}
