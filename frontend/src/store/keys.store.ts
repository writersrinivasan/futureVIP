import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface KeysState {
  openaiKey: string
  setOpenaiKey: (key: string) => void
  clearOpenaiKey: () => void
}

export const useKeysStore = create<KeysState>()(
  persist(
    (set) => ({
      openaiKey: '',
      setOpenaiKey: (key: string) => set({ openaiKey: key.trim() }),
      clearOpenaiKey: () => set({ openaiKey: '' }),
    }),
    {
      name: 'keys-storage',
    }
  )
)
