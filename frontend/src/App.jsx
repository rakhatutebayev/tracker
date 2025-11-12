import React from 'react'
import { ConfigProvider } from 'antd'
import ruRU from 'antd/locale/ru_RU'
import dayjs from 'dayjs'
import 'dayjs/locale/ru'
import { MainLayout } from './pages/MainLayout'
import 'leaflet/dist/leaflet.css'

dayjs.locale('ru')

function App() {
  return (
    <ConfigProvider locale={ruRU}>
      <MainLayout />
    </ConfigProvider>
  )
}

export default App
