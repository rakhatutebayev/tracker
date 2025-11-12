import { create } from 'zustand'

export const useTrackingStore = create((set) => ({
  devices: [],
  setDevices: (devices) => set({ devices }),

  positions: {}, // deviceId -> position
  updatePosition: (position) =>
    set((state) => ({
      positions: {
        ...state.positions,
        [position.device_id]: position,
      },
    })),

  selectedDeviceIds: [],
  setSelectedDeviceIds: (ids) => set({ selectedDeviceIds: ids }),
}))
