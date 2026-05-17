import type { AppSettings, SettingsUpdatePayload } from '@/types/settings'
import { api } from './api'

export function fetchSettings(): Promise<AppSettings> {
  return api.get<AppSettings>('/settings')
}

export function updateSettings(payload: SettingsUpdatePayload): Promise<AppSettings> {
  return api.put<AppSettings>('/settings', payload)
}
