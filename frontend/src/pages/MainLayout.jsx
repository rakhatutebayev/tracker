// CLEAN REWRITE OF FILE (previous version became corrupted)
import React, { useEffect, useState } from 'react'
import { Layout, Menu, Button, Drawer, List, Spin, message, Grid, Input } from 'antd'
import { MenuOutlined, EnvironmentOutlined, FileTextOutlined } from '@ant-design/icons'
import { LiveMap, TripsReport, SummaryReport } from '../components'
import { useTrackingStore } from '../store/trackingStore'
import { deviceService, positionService } from '../services/api'

const { Header, Sider, Content } = Layout

export function MainLayout() {
  const screens = Grid.useBreakpoint()
  const isMobile = !screens.lg
  const [collapsed, setCollapsed] = useState(false)
  const [currentPage, setCurrentPage] = useState('map')
  const [devices, setDevices] = useState([])
  const [deviceQuery, setDeviceQuery] = useState('')
  const [loadingDevices, setLoadingDevices] = useState(false)
  const [selectedDeviceId, setSelectedDeviceId] = useState(null)
  const [deviceDrawerOpen, setDeviceDrawerOpen] = useState(false)
  const { selectedDeviceIds, setSelectedDeviceIds, setDevices: storeSetDevices, updatePosition } = useTrackingStore()

  useEffect(() => {
    // restore persisted UI state
    try {
      const savedPage = localStorage.getItem('ui.currentPage')
      if (savedPage) setCurrentPage(savedPage)
      const savedSel = localStorage.getItem('ui.selectedDeviceIds')
      if (savedSel) {
        const ids = JSON.parse(savedSel)
        if (Array.isArray(ids) && ids.length) {
          setSelectedDeviceIds(ids)
          setSelectedDeviceId(ids[0])
        }
      }
    } catch {}

    loadDevices()
    loadLatestPositions()
  }, [])

  const loadLatestPositions = async () => {
    try {
      const response = await positionService.getLatestPositions()
      if (response.data && Array.isArray(response.data)) {
        response.data.forEach(pos => updatePosition(pos))
      }
    } catch (err) {
      console.error('Error loading positions:', err)
    }
  }

  const loadDevices = async () => {
    setLoadingDevices(true)
    try {
      const response = await deviceService.listDevices()
      setDevices(response.data)
      storeSetDevices(response.data)
      if (response.data.length > 0) {
        setSelectedDeviceId(response.data[0].id)
        setSelectedDeviceIds([response.data[0].id])
      }
    } catch (err) {
      message.error('Ошибка загрузки списка машин')
      console.error(err)
    } finally {
      setLoadingDevices(false)
    }
  }

  const handleSelectDevices = (deviceIds) => {
    setSelectedDeviceIds(deviceIds)
    try { localStorage.setItem('ui.selectedDeviceIds', JSON.stringify(deviceIds)) } catch {}
  }

  const filteredDevices = devices.filter(d => d.name.toLowerCase().includes(deviceQuery.toLowerCase()))

  const menuItems = [
    { key: 'map', icon: <EnvironmentOutlined />, label: '🗺️ Реал-тайм карта' },
    { key: 'trips', icon: <FileTextOutlined />, label: '📊 Отчет по маршрутам' },
    { key: 'summary', icon: <FileTextOutlined />, label: '📈 Итоговый отчет' },
  ]

  return (
    <Layout style={{ height: '100vh', overflow: 'hidden' }}>
      <Header style={{ background: '#001529', color: 'white', display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 20px' }}>
        <div style={{ fontSize: '18px', fontWeight: 'bold' }}>🚚 GPS Трекер</div>
        <div style={{ display: 'flex', gap: 8 }}>
          <Button
            type="text"
            icon={<MenuOutlined />}
            onClick={() => {
              if (isMobile) setDeviceDrawerOpen(true)
              else setCollapsed(!collapsed)
            }}
            style={{ color: 'white' }}
          />
        </div>
      </Header>

      <Layout style={{ height: 'calc(100vh - 64px)' }}>
        <Sider
          trigger={null}
            collapsible
          collapsed={isMobile ? true : collapsed}
          width={250}
          collapsedWidth={isMobile ? 0 : 80}
          breakpoint="lg"
          onBreakpoint={(broken) => broken && setCollapsed(true)}
          theme="dark"
          style={{ overflow: 'auto', height: '100%', position: 'fixed', left: 0, top: 64, bottom: 0, zIndex: 100 }}
        >
          <Menu theme="dark" mode="inline" selectedKeys={[currentPage]} items={menuItems} onClick={(e) => { setCurrentPage(e.key); try { localStorage.setItem('ui.currentPage', e.key) } catch {} }} />
          <div style={{ padding: 20, borderTop: '1px solid #434343' }}>
            <p style={{ color: '#fff', marginBottom: 10, fontWeight: 'bold' }}>Машины</p>
            <Input.Search
              placeholder="Поиск машины..."
              allowClear
              value={deviceQuery}
              onChange={(e) => setDeviceQuery(e.target.value)}
              style={{ marginBottom: 12 }}
              size="small"
            />
            <Spin spinning={loadingDevices}>
              <List
                dataSource={filteredDevices}
                renderItem={(device) => (
                  <div
                    key={device.id}
                    onClick={() => { setSelectedDeviceId(device.id); handleSelectDevices([device.id]) }}
                    style={{
                      padding: 8,
                      marginBottom: 8,
                      background: selectedDeviceIds.includes(device.id) ? '#177ddc' : '#434343',
                      borderRadius: 4,
                      cursor: 'pointer',
                      color: 'white',
                      fontSize: 12,
                    }}
                  >
                    {device.name}
                  </div>
                )}
              />
            </Spin>
          </div>
        </Sider>

        <Content style={{ marginLeft: isMobile ? 0 : (collapsed ? 80 : 250), overflow: 'auto', transition: 'margin-left 0.3s', height: '100%' }}>
          {currentPage === 'map' && <LiveMap />}
          {currentPage === 'trips' && (
            <div style={{ padding: 20 }}>
              <TripsReport
                devices={devices}
                selectedDeviceId={selectedDeviceId}
                onDeviceChange={(id) => { setSelectedDeviceId(id); setSelectedDeviceIds([id]) }}
              />
            </div>
          )}
          {currentPage === 'summary' && (
            <div style={{ padding: 20 }}>
              <SummaryReport
                devices={devices}
                selectedDeviceId={selectedDeviceId}
                onDeviceChange={(id) => { setSelectedDeviceId(id); setSelectedDeviceIds([id]) }}
              />
            </div>
          )}
        </Content>
      </Layout>

      <Drawer title="Машины" placement="left" onClose={() => setDeviceDrawerOpen(false)} open={deviceDrawerOpen} bodyStyle={{ padding: 16 }}>
        <Input.Search
          placeholder="Поиск машины..."
          allowClear
          value={deviceQuery}
          onChange={(e) => setDeviceQuery(e.target.value)}
          style={{ marginBottom: 12 }}
          size="middle"
        />
        <Spin spinning={loadingDevices}>
          <List
            dataSource={filteredDevices}
            renderItem={(device) => (
              <div
                key={device.id}
                onClick={() => { setSelectedDeviceId(device.id); handleSelectDevices([device.id]); setDeviceDrawerOpen(false) }}
                style={{
                  padding: 10,
                  marginBottom: 10,
                  background: selectedDeviceIds.includes(device.id) ? '#177ddc' : '#f0f2f5',
                  borderRadius: 6,
                  cursor: 'pointer',
                }}
              >
                {device.name}
              </div>
            )}
          />
        </Spin>
      </Drawer>
    </Layout>
  )
}
