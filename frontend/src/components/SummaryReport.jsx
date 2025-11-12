import React, { useState, useEffect } from 'react'
import { Card, Select, Space, Button, Statistic, Row, Col, Spin, message } from 'antd'
import { ReloadOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import { reportService } from '../services/api'
import RangePickerWithPresets from './RangePresets'

export function SummaryReport({ devices, selectedDeviceId, onDeviceChange }) {
  const [summary, setSummary] = useState(null)
  const [loading, setLoading] = useState(false)
  const [fromDate, setFromDate] = useState(dayjs().startOf('month'))
  const [toDate, setToDate] = useState(dayjs().endOf('month'))

  useEffect(() => {
    if (selectedDeviceId) {
      loadSummary()
    }
  }, [selectedDeviceId])

  const loadSummary = async () => {
    if (!selectedDeviceId) return

    setLoading(true)
    try {
      const response = await reportService.getSummaryReport(selectedDeviceId, fromDate, toDate)
      setSummary(response.data)
    } catch (err) {
      message.error('Ошибка загрузки отчета')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const getPeriodLabel = () => {
    if (toDate.diff(fromDate, 'day') <= 7) {
      return 'за неделю'
    } else if (toDate.diff(fromDate, 'day') <= 31) {
      return 'за месяц'
    } else {
      return 'за период'
    }
  }

  const handleRangeChange = (vals) => {
    if (!vals) return
    const [from, to] = vals
    setFromDate(from)
    setToDate(to)
    // Auto refresh after brief debounce for better UX
    setTimeout(() => loadSummary(), 200)
  }

  return (
    <Card
      title={`Итоговый отчет ${getPeriodLabel()}`}
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
          <RangePickerWithPresets value={[fromDate, toDate]} onChange={handleRangeChange} />
          <Button
            type="primary"
            icon={<ReloadOutlined />}
            onClick={loadSummary}
            loading={loading}
          >
            Обновить
          </Button>
        </Space>
      }
    >
      <Spin spinning={loading}>
        {summary ? (
          <Row gutter={[12, 12]} wrap>
            <Col xs={12} sm={12} md={6}>
              <Statistic
                title="Поездок"
                value={summary.trip_count}
                valueStyle={{ color: '#1890ff' }}
              />
            </Col>
            <Col xs={12} sm={12} md={6}>
              <Statistic
                title="Расстояние (км)"
                value={summary.total_distance_km}
                precision={2}
                valueStyle={{ color: '#52c41a' }}
              />
            </Col>
            <Col xs={12} sm={12} md={6}>
              <Statistic
                title="Время в пути (ч)"
                value={summary.total_duration_hours}
                precision={2}
                valueStyle={{ color: '#faad14' }}
              />
            </Col>
            <Col xs={12} sm={12} md={6}>
              <Statistic
                title="Средн. скорость"
                value={summary.avg_speed}
                suffix="км/ч"
                precision={1}
                valueStyle={{ color: '#f5222d' }}
              />
            </Col>
            <Col xs={12} sm={12} md={6}>
              <Statistic
                title="Макс. скорость"
                value={summary.max_speed}
                suffix="км/ч"
                precision={1}
                valueStyle={{ color: '#722ed1' }}
              />
            </Col>
            <Col xs={24}>
              <p style={{ marginTop: '20px', color: '#666' }}>
                <strong>Период:</strong> {fromDate.format('YYYY-MM-DD')} по{' '}
                {toDate.format('YYYY-MM-DD')}
              </p>
            </Col>
          </Row>
        ) : (
          <p>Нет данных для отображения</p>
        )}
      </Spin>
    </Card>
  )
}
