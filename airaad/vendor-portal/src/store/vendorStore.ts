import { create } from 'zustand';

interface ClaimFlowState {
  selectedVendorId: string | null;
  selectedVendorName: string | null;
  claimStep: 'search' | 'verify' | 'setup' | 'welcome';
  setSelectedVendor: (id: string, name: string) => void;
  setClaimStep: (step: ClaimFlowState['claimStep']) => void;
  resetClaimFlow: () => void;
}

export const useVendorStore = create<ClaimFlowState>((set) => ({
  selectedVendorId: null,
  selectedVendorName: null,
  claimStep: 'search',
  setSelectedVendor: (id, name) => set({ selectedVendorId: id, selectedVendorName: name }),
  setClaimStep: (step) => set({ claimStep: step }),
  resetClaimFlow: () => set({ selectedVendorId: null, selectedVendorName: null, claimStep: 'search' }),
}));
