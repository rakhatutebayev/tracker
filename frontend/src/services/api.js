import axios from 'axios'

// Prefer build-time configured API base, with a sensible localhost fallback.
// This prevents the SPA static server from catching '/api' and returning HTML.
const API_BASE =
  (typeof import.meta !== 'undefined' && import.meta.env && import.meta.env.VITE_API_BASE)
    || (typeof window !== 'undefined' && window.location.hostname === 'localhost'
      ? 'http://localhost:8001/api'
      : '/api')

const api = axios.create({
  baseURL: API_BASE,
})

export const deviceService = {
  listDevices: () => api.get('/devices'),
  getDevice: (id) => api.get(`/devices/${id}`),
}

export const positionService = {
  getLatestPositions: () => api.get('/positions/latest'),
  getDevicePositions: (deviceId, limit = 100) => api.get(`/positions/${deviceId}`, { params: { limit } }),
  getHistory: (deviceId, fromDate, toDate) =>
    api.get('/positions/history', {
      params: {
        device_id: deviceId,
        from_date: fromDate.toISOString(),
        to_date: toDate.toISOString(),
      },
    }),
}

export const reportService = {
  getTripReport: (deviceId, fromDate, toDate) =>
    api.post('/reports/trips', {
      device_id: deviceId,
      from_date: fromDate.toISOString(),
      to_date: toDate.toISOString(),
    }),

  getSummaryReport: (deviceId, fromDate, toDate) =>
    api.get('/reports/summary', {
      params: {
        device_id: deviceId,
        from_date: fromDate.toISOString(),
        to_date: toDate.toISOString(),
      },
    }),
}

export const stopService = {
  getStops: (deviceId, fromDate, toDate) =>
    api.get('/stops', {
      params: {
        device_id: deviceId,
        from_date: fromDate.toISOString(),
        to_date: toDate.toISOString(),
      },
    }),
}

export default api
