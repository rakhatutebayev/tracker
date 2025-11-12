import React, { useEffect, useState } from 'react'
import { Card, Table, Select, Button, Space, Spin, message, Tooltip, Grid } from 'antd'
import { DownloadOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import utc from 'dayjs/plugin/utc'
import { reportService } from '../services/api'
import RangePickerWithPresets from './RangePresets'

dayjs.extend(utc)

export function TripsReport({ devices, selectedDeviceId, onDeviceChange }) {
  const screens = Grid.useBreakpoint()
  const [trips, setTrips] = useState([])
  const [summary, setSummary] = useState(null)
  const [loading, setLoading] = useState(false)
  const [fromDate, setFromDate] = useState(dayjs().startOf('month'))
  const [toDate, setToDate] = useState(dayjs().endOf('month'))

  useEffect(() => {
    if (selectedDeviceId) {
      loadTrips()
    }
  }, [selectedDeviceId])

  const loadTrips = async () => {
    if (!selectedDeviceId) return

    setLoading(true)
    try {
      const response = await reportService.getTripReport(selectedDeviceId, fromDate, toDate)
      setTrips(response.data.trips || [])
      setSummary(response.data)
    } catch (err) {
      message.error('Ошибка загрузки отчета')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const handleRangeChange = (vals) => {
    if (!vals) return
    const [from, to] = vals
    setFromDate(from)
    setToDate(to)
    setLoading(true)
    setTimeout(() => { loadTrips() }, 200)
  }

  const exportToCSV = () => {
    if (!trips || trips.length === 0) {
      message.warning('Нет данных для экспорта')
      return
    }

    const headers = [
      'ID','Название машины','Пункт выезда','Дата выезда','Время выезда','Пункт приезда','Дата приезда','Время приезда','Время в пути (ч)','Расстояние (км)','Средняя скорость','Макс скорость'
    ]

    const rows = trips.map((trip) => [
      trip.trip_id,
      trip.device_name,
      trip.start_point,
      new Date(trip.start_time).toLocaleDateString('ru-RU'),
      new Date(trip.start_time).toLocaleTimeString('ru-RU'),
      trip.end_point,
      new Date(trip.end_time).toLocaleDateString('ru-RU'),
      new Date(trip.end_time).toLocaleTimeString('ru-RU'),
      trip.duration_hours.toFixed(2),
      trip.distance_km.toFixed(2),
      (trip.avg_speed || 0).toFixed(2),
      (trip.max_speed || 0).toFixed(2),
    ])

    const csv = [
      headers.join(','),
      ...rows.map((row) => row.map((cell) => `"${cell}"`).join(',')),
    ].join('\n')

    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
    const link = document.createElement('a')
    const url = URL.createObjectURL(blob)
    link.setAttribute('href', url)
    link.setAttribute('download', `trips_${selectedDeviceId}_${fromDate.format('YYYY-MM-DD')}.csv`)
    link.style.visibility = 'hidden'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  // Build responsive columns manually for better control across screen sizes
  const isMobile = !screens.md
  const isTablet = screens.md && !screens.lg
  const isDesktop = screens.lg

  const baseCols = [
    isDesktop && {
      title: 'ID',
      dataIndex: 'trip_id',
      key: 'trip_id',
      width: 70,
    },
    {
      title: isMobile ? 'Старт' : 'Пункт выезда',
      dataIndex: 'start_point',
      key: 'start_point',
      width: isMobile ? 160 : 200,
      ellipsis: true,
      render: (text) => <Tooltip title={text}>{text}</Tooltip>,
    },
    {
      title: isMobile ? 'Время' : 'Дата/Время выезда',
      dataIndex: 'start_time',
      key: 'start_time',
      width: 180,
      render: (text) => new Date(text).toLocaleString('ru-RU'),
    },
    !isMobile && {
      title: 'Пункт приезда',
      dataIndex: 'end_point',
      key: 'end_point',
      width: 200,
      ellipsis: true,
      render: (text) => <Tooltip title={text}>{text}</Tooltip>,
    },
    !isMobile && {
      title: 'Дата/Время приезда',
      dataIndex: 'end_time',
      key: 'end_time',
      width: 180,
      render: (text) => new Date(text).toLocaleString('ru-RU'),
    },
    (isTablet || isDesktop) && {
      title: 'Время в пути (ч)',
      dataIndex: 'duration_hours',
      key: 'duration_hours',
      width: 120,
      render: (text) => text.toFixed(2),
    },
    (isTablet || isDesktop) && {
      title: 'Расстояние (км)',
      dataIndex: 'distance_km',
      key: 'distance_km',
      width: 120,
      render: (text) => text.toFixed(2),
    },
    isDesktop && {
      title: 'Средн. скорость',
      dataIndex: 'avg_speed',
      key: 'avg_speed',
      width: 110,
      render: (text) => (text || 0).toFixed(1),
    },
    isDesktop && {
      title: 'Макс. скорость',
      dataIndex: 'max_speed',
      key: 'max_speed',
      width: 110,
      render: (text) => (text || 0).toFixed(1),
    },
  ].filter(Boolean)

  return (
    <Card
      title="Отчет по маршрутам (поездкам)"
      extra={
        <Space>
          <Select
            style={{ width: '150px' }}
            placeholder="Выберите машину"
            value={selectedDeviceId}
            onChange={onDeviceChange}
            options={devices.map((d) => ({
              label: d.name,
              value: d.id,
            }))}
          />
          <RangePickerWithPresets
            value={[fromDate, toDate]}
            onChange={handleRangeChange}
          />
          <Button type="primary" onClick={loadTrips} loading={loading}>
            Обновить
          </Button>
          <Button icon={<DownloadOutlined />} onClick={exportToCSV}>
            CSV
          </Button>
        </Space>
      }
    >
      {summary && (
        <div style={{ marginBottom: '20px', padding: '10px', background: '#f0f2f5', borderRadius: '4px' }}>
          <p>
            <strong>Машина:</strong> {summary.device_name} | <strong>Период:</strong> {summary.period}
          </p>
          <p>
            <strong>Поездок:</strong> {summary.trip_count} | <strong>Расстояние:</strong>{' '}
            {summary.total_distance.toFixed(2)} км | <strong>Время в пути:</strong>{' '}
            {(summary.total_duration / 3600).toFixed(2)} ч
          </p>
        </div>
      )}

      <Spin spinning={loading}>
        <div className="responsive-scroll-wrapper">
          <Table
            columns={baseCols}
            dataSource={trips.map((t) => ({ ...t, key: t.trip_id }))}
            size="small"
            tableLayout="auto"
            pagination={{ pageSize: 20, showSizeChanger: true, responsive: true, simple: isMobile }}
            scroll={{ x: true }}
          />
        </div>
      </Spin>
    </Card>
  )
}
