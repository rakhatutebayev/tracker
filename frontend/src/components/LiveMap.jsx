import React, { useEffect, useRef, useCallback, useState } from 'react'
import { MapContainer, TileLayer, Marker, Popup, Polyline, CircleMarker, useMap } from 'react-leaflet'
import L from 'leaflet'
import { useTrackingStore } from '../store/trackingStore'
import { useWebSocket } from '../hooks/useWebSocket'
import dayjs from 'dayjs'
import { positionService, reportService, stopService } from '../services/api'
import RangePickerWithPresets from './RangePresets'

// Custom marker icons
const createMarkerIcon = (color = 'blue') => {
  return L.divIcon({
    html: `
      <div style="
        background: ${color};
        width: 30px;
        height: 30px;
        border-radius: 50%;
        border: 3px solid white;
        box-shadow: 0 0 10px rgba(0,0,0,0.3);
        display: flex;
        align-items: center;
        justify-content: center;
      ">
        <span style="color: white; font-weight: bold; font-size: 14px;">🚚</span>
      </div>
    `,
    iconSize: [30, 30],
    className: 'custom-marker',
  })
}

export function LiveMap() {
  const { positions, selectedDeviceIds, updatePosition } = useTrackingStore()
  const [historyRange, setHistoryRange] = useState([dayjs().startOf('day'), dayjs().endOf('day')])
  const [historyPositions, setHistoryPositions] = useState([])
  const [loadingHistory, setLoadingHistory] = useState(false)
  const [showHistory, setShowHistory] = useState(true)
  const [segmentByTrips, setSegmentByTrips] = useState(true)
  const [tripSegments, setTripSegments] = useState([]) // array of arrays of latlngs
  const [tripMarkers, setTripMarkers] = useState([]) // {start:[lat,lon,time], end:[lat,lon,time]}
  const [stops, setStops] = useState([]) // [{latitude, longitude, arrival_time, departure_time, duration}]

  const handleWebSocketMessage = useCallback((msg) => {
    if (msg.type === 'position_update') {
      updatePosition(msg.data)
    }
  }, [updatePosition])

  useWebSocket(selectedDeviceIds, handleWebSocketMessage)

  // Use a stable ref for initial center so MapContainer doesn't re-center on re-renders
  const initialCenterRef = useRef([43.2379, 76.9387]) // Almaty

  // Recenter on selection change (not on every live update)
  function FocusOnSelect({ selectedId }) {
    const map = useMap()
    const lastSelectedRef = useRef(null)
    const userInteractedRef = useRef(false)

    // Mark user interaction so we don't auto-center again after manual pan
    useEffect(() => {
      const handleMoveStart = () => {
        userInteractedRef.current = true
      }
      map.on('movestart', handleMoveStart)
      return () => {
        map.off('movestart', handleMoveStart)
      }
    }, [map])

    useEffect(() => {
      if (!selectedId) return
      // Only center when selection changes explicitly, not after pan
      if (lastSelectedRef.current === selectedId) return
      const pos = positions[selectedId]
      if (pos) {
        map.setView([pos.latitude, pos.longitude], Math.max(map.getZoom(), 14), { animate: true })
        lastSelectedRef.current = selectedId
        // Reset user interaction flag so a new manual pan can occur
        userInteractedRef.current = false
      }
    }, [selectedId, map])

    return null
  }

  // Controls overlay: Fit to selected
  function MapControls() {
    const map = useMap()

    const fitToCoords = (coords) => {
      if (!coords || coords.length === 0) return
      if (coords.length === 1) {
        map.setView(coords[0], Math.max(map.getZoom(), 15), { animate: true })
      } else {
        const bounds = L.latLngBounds(coords)
        map.fitBounds(bounds, { padding: [40, 40] })
      }
    }

    const handleFit = () => {
      const coords = selectedDeviceIds
        .map(id => positions[id])
        .filter(Boolean)
        .map(p => [p.latitude, p.longitude])
      if (coords.length === 0) return
      if (coords.length === 1) {
        map.setView(coords[0], Math.max(map.getZoom(), 15), { animate: true })
      } else {
        const bounds = L.latLngBounds(coords)
        map.fitBounds(bounds, { padding: [40, 40] })
      }
    }

    const fetchHistory = async () => {
      if (!selectedDeviceIds.length) return
      setLoadingHistory(true)
      try {
        // For now fetch history for the first selected device
        const [from, to] = historyRange
        const resp = await positionService.getHistory(selectedDeviceIds[0], from, to)
        setHistoryPositions(resp.data || [])

        if (segmentByTrips) {
          const tripsResp = await reportService.getTripReport(selectedDeviceIds[0], from, to)
          const trips = (tripsResp.data && tripsResp.data.trips) || []

          const positionsWithTs = (resp.data || []).map(p => ({
            ...p,
            _ts: new Date(p.fix_time).getTime(),
          }))

          const segments = trips.map((t) => {
            const startTs = new Date(t.start_time).getTime()
            const endTs = new Date(t.end_time).getTime()
            const coords = positionsWithTs
              .filter(p => p._ts >= startTs && p._ts <= endTs)
              .map(p => [p.latitude, p.longitude])
            return coords
          }).filter(seg => seg.length > 0)

          setTripSegments(segments)
          setTripMarkers(trips.map(t => ({
            start: { lat: t.start_lat, lon: t.start_lon, time: t.start_time },
            end: { lat: t.end_lat, lon: t.end_lon, time: t.end_time },
          })))

          // Auto-fit to all segments
          const allCoords = segments.flat()
          fitToCoords(allCoords)
        } else {
          setTripSegments([])
          setTripMarkers([])

          // Auto-fit to the single polyline history
          const coords = (resp.data || []).map(p => [p.latitude, p.longitude])
          fitToCoords(coords)
        }

        // Fetch stops for the same device and range
        try {
          const s = await stopService.getStops(selectedDeviceIds[0], from, to)
          setStops(s.data || [])
        } catch (e) {
          console.warn('Stops not available', e)
          setStops([])
        }
      } catch (e) {
        console.error('Failed to load history', e)
      } finally {
        setLoadingHistory(false)
      }
    }

    return (
      <div style={{ position: 'absolute', top: 60, right: 10, display: 'flex', flexDirection: 'column', gap: 8, zIndex: 1001, width: 300 }}>
        <div style={{ background: 'rgba(255,255,255,0.95)', padding: 10, borderRadius: 8, boxShadow: '0 2px 8px rgba(0,0,0,0.15)' }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            <RangePickerWithPresets
              value={historyRange}
              onChange={(vals) => vals && setHistoryRange(vals)}
              style={{ width: '100%' }}
            />
            <div style={{ display: 'flex', gap: 6 }}>
              <button
                onClick={fetchHistory}
                disabled={!selectedDeviceIds.length || loadingHistory}
                style={{ flex: 1, background: '#177ddc', color: '#fff', border: 'none', borderRadius: 6, padding: '6px 8px', cursor: 'pointer' }}
              >
                {loadingHistory ? 'Загрузка...' : 'История'}
              </button>
              <button
                onClick={() => setShowHistory((s) => !s)}
                style={{ flex: 1, background: showHistory ? '#faad14' : '#434343', color: '#fff', border: 'none', borderRadius: 6, padding: '6px 8px', cursor: 'pointer' }}
              >
                {showHistory ? 'Скрыть' : 'Показать'}
              </button>
            </div>
            <div style={{ display: 'flex', gap: 6 }}>
              <button
                onClick={() => setSegmentByTrips((v) => !v)}
                style={{ flex: 1, background: segmentByTrips ? '#722ed1' : '#434343', color: '#fff', border: 'none', borderRadius: 6, padding: '6px 8px', cursor: 'pointer' }}
              >
                {segmentByTrips ? 'По поездкам' : 'Одна линия'}
              </button>
              <div style={{ flex: 1, fontSize: 12, color: '#555', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                {segmentByTrips && tripSegments.length ? `Линий: ${tripSegments.length}` : historyPositions.length ? `Точек: ${historyPositions.length}` : ''}
              </div>
            </div>
            <button
              onClick={handleFit}
              style={{ background: '#52c41a', color: '#fff', border: 'none', borderRadius: 6, padding: '6px 8px', cursor: 'pointer' }}
            >
              ⤢ Выбранные
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
  <MapContainer center={initialCenterRef.current} zoom={12} className="leaflet-container" style={{ height: '100%', width: '100%' }}>
      <FocusOnSelect selectedId={selectedDeviceIds[0]} />
      <MapControls />
      {/* Map layers: OSM by default; 2GIS optional via VITE_2GIS_KEY */}
      {(() => {
        const provider = (typeof import.meta !== 'undefined' && import.meta.env && import.meta.env.VITE_MAP_PROVIDER) || 'osm'
        const key = (typeof import.meta !== 'undefined' && import.meta.env && import.meta.env.VITE_2GIS_KEY) || null
        if (provider === '2gis' && key) {
          // 2GIS tile template example; replace with official if needed
          return (
            <TileLayer
              url={`https://tile2.maps.2gis.com/tiles?x={x}&y={y}&z={z}&key=${key}`}
              attribution='© 2GIS'
              maxZoom={19}
            />
          )
        }
        return (
          <TileLayer
            url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
            attribution='© OpenStreetMap contributors'
            maxZoom={19}
          />
        )
      })()}

      {/* Render markers for all selected devices */}
      {selectedDeviceIds.map((deviceId) => {
        const pos = positions[deviceId]
        if (!pos) return null

        return (
          <Marker
            key={deviceId}
            position={[pos.latitude, pos.longitude]}
            icon={createMarkerIcon('blue')}
          >
            <Popup>
              <div style={{ minWidth: '200px' }}>
                <h4>{pos.device_name}</h4>
                <p><strong>Широта:</strong> {pos.latitude.toFixed(4)}</p>
                <p><strong>Долгота:</strong> {pos.longitude.toFixed(4)}</p>
                <p><strong>Скорость:</strong> {(pos.speed || 0).toFixed(1)} км/ч</p>
                <p><strong>Время:</strong> {new Date(pos.fix_time).toLocaleString('ru-RU')}</p>
                <div className="live-indicator" style={{ marginTop: '10px', color: 'red' }}>
                  ● Live
                </div>
              </div>
            </Popup>
          </Marker>
        )
      })}

      {/* History: either segmented by trips or single polyline */}
      {showHistory && segmentByTrips && tripSegments.length > 0 && (
        tripSegments.map((seg, idx) => (
          <Polyline
            key={`seg-${idx}`}
            positions={seg}
            pathOptions={{ color: [
              '#ff4d4f', '#52c41a', '#1890ff', '#faad14', '#722ed1', '#13c2c2', '#eb2f96'
            ][idx % 7], weight: 4, opacity: 0.8 }}
          />
        ))
      )}
      {showHistory && segmentByTrips && tripMarkers.map((m, idx) => (
        <React.Fragment key={`mk-${idx}`}>
          <CircleMarker center={[m.start.lat, m.start.lon]} radius={7} pathOptions={{ color: '#2f54eb', fillColor: '#2f54eb', fillOpacity: 0.9 }}>
            <Popup>
              <div style={{ fontSize: 12 }}>
                <strong>Выезд</strong><br/>
                Координаты: {m.start.lat.toFixed(4)}, {m.start.lon.toFixed(4)}<br/>
                Время: {new Date(m.start.time).toLocaleString('ru-RU')}
              </div>
            </Popup>
          </CircleMarker>
          <CircleMarker center={[m.end.lat, m.end.lon]} radius={7} pathOptions={{ color: '#a8071a', fillColor: '#a8071a', fillOpacity: 0.9 }}>
            <Popup>
              <div style={{ fontSize: 12 }}>
                <strong>Прибытие</strong><br/>
                Координаты: {m.end.lat.toFixed(4)}, {m.end.lon.toFixed(4)}<br/>
                Время: {new Date(m.end.time).toLocaleString('ru-RU')}
                {m.start.time && m.end.time && (
                  <>
                    <br/>
                    В пути: {((new Date(m.end.time).getTime() - new Date(m.start.time).getTime())/3600000).toFixed(2)} ч
                  </>
                )}
              </div>
            </Popup>
          </CircleMarker>
        </React.Fragment>
      ))}
      {showHistory && !segmentByTrips && historyPositions.length > 1 && (
        <Polyline
          positions={historyPositions.map(p => [p.latitude, p.longitude])}
          pathOptions={{ color: '#ff4d4f', weight: 4, opacity: 0.7 }}
        />
      )}

      {/* Stop markers: small circles showing arrival, optional departure, and coords */}
      {showHistory && stops.map((s, idx) => (
        <CircleMarker key={`stop-${idx}`} center={[s.latitude, s.longitude]} radius={5} pathOptions={{ color: '#595959', fillColor: '#bfbfbf', fillOpacity: 0.95 }}>
          <Popup>
            <div style={{ fontSize: 12 }}>
              <strong>Остановка</strong><br/>
              Координаты: {s.latitude.toFixed(4)}, {s.longitude.toFixed(4)}<br/>
              Прибытие: {new Date(s.arrival_time).toLocaleString('ru-RU')}
              {s.departure_time && (
                <>
                  <br/>
                  Убытие: {new Date(s.departure_time).toLocaleString('ru-RU')}
                </>
              )}
            </div>
          </Popup>
        </CircleMarker>
      ))}
    </MapContainer>
  )
}
