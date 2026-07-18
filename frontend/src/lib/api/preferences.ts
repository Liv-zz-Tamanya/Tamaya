import { apiFetch } from './client';

export type NightChatPreference = {
  open_time: string;
  timezone: string;
};

export function getNightChatPreference(): Promise<NightChatPreference> {
  return apiFetch<NightChatPreference>('/api/v1/me/preferences/night-chat');
}

export function updateNightChatPreference(
  preference: NightChatPreference,
): Promise<NightChatPreference> {
  return apiFetch<NightChatPreference>('/api/v1/me/preferences/night-chat', {
    method: 'PUT',
    body: preference,
  });
}
