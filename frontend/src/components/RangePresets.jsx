import React from 'react'
import { DatePicker, Space, Segmented } from 'antd'
import dayjs from 'dayjs'

const { RangePicker } = DatePicker

const presetRanges = () => {
  const now = dayjs()
  const thisWeek = [now.startOf('week'), now.endOf('week')]
  const lastWeekStart = now.subtract(1, 'week').startOf('week')
  const lastWeekEnd = now.subtract(1, 'week').endOf('week')
  const lastWeek = [lastWeekStart, lastWeekEnd]
  const thisMonth = [now.startOf('month'), now.endOf('month')]
  const lastMonthStart = now.subtract(1, 'month').startOf('month')
  const lastMonthEnd = now.subtract(1, 'month').endOf('month')
  const lastMonth = [lastMonthStart, lastMonthEnd]
  const today = [now.startOf('day'), now.endOf('day')]

  return [
    { label: 'Сегодня', value: today },
    { label: 'Эта неделя', value: thisWeek },
    { label: 'Прошлая неделя', value: lastWeek },
    { label: 'Этот месяц', value: thisMonth },
    { label: 'Прошлый месяц', value: lastMonth },
  ]
}

export function RangePickerWithPresets({ value, onChange, style }) {
  const presets = presetRanges()

  return (
    <Space size={8} wrap>
      <RangePicker
        value={value}
        onChange={(vals) => onChange(vals)}
        showTime={false}
        format="YYYY-MM-DD"
        presets={presets}
        style={style}
      />
    </Space>
  )
}

export default RangePickerWithPresets
