import { create } from 'zustand';

type DiscoveryView = 'ar' | 'map' | 'list';

interface LocationState {
  lat: number;
  lng: number;
  accuracy: number;
  heading: number | null;
  timestamp: number;
}

interface DiscoveryState {
  activeView: DiscoveryView;
  setActiveView: (view: DiscoveryView) => void;
  location: LocationState | null;
  setLocation: (loc: LocationState) => void;
  locationError: string | null;
  setLocationError: (err: string | null) => void;
  locationPermission: 'prompt' | 'granted' | 'denied' | 'unknown';
  setLocationPermission: (perm: 'prompt' | 'granted' | 'denied' | 'unknown') => void;
  searchQuery: string;
  setSearchQuery: (q: string) => void;
  selectedTags: string[];
  setSelectedTags: (tags: string[]) => void;
  toggleTag: (tag: string) => void;
  radiusKm: number;
  setRadiusKm: (r: number) => void;
  sortBy: 'relevance' | 'distance' | 'rating';
  setSortBy: (s: 'relevance' | 'distance' | 'rating') => void;
  selectedCity: string | null;
  setSelectedCity: (city: string | null) => void;
  selectedArea: string | null;
  setSelectedArea: (area: string | null) => void;
}

export const useDiscoveryStore = create<DiscoveryState>()((set) => ({
  activeView: 'ar',
  setActiveView: (view) => set({ activeView: view }),

  location: null,
  setLocation: (loc) => set({ location: loc, locationError: null }),

  locationError: null,
  setLocationError: (err) => set({ locationError: err }),

  locationPermission: 'unknown',
  setLocationPermission: (perm) => set({ locationPermission: perm }),

  searchQuery: '',
  setSearchQuery: (q) => set({ searchQuery: q }),

  selectedTags: [],
  setSelectedTags: (tags) => set({ selectedTags: tags }),
  toggleTag: (tag) =>
    set((state) => ({
      selectedTags: state.selectedTags.includes(tag)
        ? state.selectedTags.filter((t) => t !== tag)
        : [...state.selectedTags, tag],
    })),

  radiusKm: 2,
  setRadiusKm: (r) => set({ radiusKm: r }),

  sortBy: 'relevance',
  setSortBy: (s) => set({ sortBy: s }),

  selectedCity: null,
  setSelectedCity: (city) => set({ selectedCity: city }),

  selectedArea: null,
  setSelectedArea: (area) => set({ selectedArea: area }),
}));
