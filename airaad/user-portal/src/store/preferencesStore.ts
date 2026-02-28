import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface NotificationPrefs {
  push: boolean;
  email: boolean;
}

interface PreferencesState {
  searchRadius: number;
  notifications: NotificationPrefs;
  locationSharing: boolean;
  dataCollection: boolean;
  setSearchRadius: (radius: number) => void;
  setNotifications: (prefs: NotificationPrefs) => void;
  setLocationSharing: (enabled: boolean) => void;
  setDataCollection: (enabled: boolean) => void;
}

export const usePreferencesStore = create<PreferencesState>()(
  persist(
    (set) => ({
      searchRadius: 2,
      notifications: { push: true, email: false },
      locationSharing: true,
      dataCollection: true,

      setSearchRadius: (radius) => set({ searchRadius: radius }),
      setNotifications: (prefs) => set({ notifications: prefs }),
      setLocationSharing: (enabled) => set({ locationSharing: enabled }),
      setDataCollection: (enabled) => set({ dataCollection: enabled }),
    }),
    {
      name: 'airad-user-preferences',
    },
  ),
);
