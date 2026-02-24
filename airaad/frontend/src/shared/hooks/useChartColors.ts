import { useMemo } from 'react';
import { useUIStore } from '@/shared/store/uiStore';

function getCSSVar(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

export interface ChartColors {
  gridStroke: string;
  tickFill: string;
  tooltipBg: string;
  tooltipBorder: string;
  barOrange: string;
  barTeal: string;
  barCrimson: string;
  fallback: string;
}

export function useChartColors(): ChartColors {
  const theme = useUIStore((s) => s.theme);

  return useMemo(() => {
    return {
      gridStroke:    getCSSVar('--border-default')   || (theme === 'dark' ? '#2A2A2A' : '#E7E5E4'),
      tickFill:      getCSSVar('--text-secondary')   || (theme === 'dark' ? '#A8A29E' : '#6B7280'),
      tooltipBg:     getCSSVar('--surface-card')     || (theme === 'dark' ? '#1C1C1C' : '#FFFFFF'),
      tooltipBorder: getCSSVar('--border-default')   || (theme === 'dark' ? '#2A2A2A' : '#E7E5E4'),
      barOrange:     getCSSVar('--brand-orange')      || '#F97316',
      barTeal:       getCSSVar('--brand-teal')        || '#0D9488',
      barCrimson:    getCSSVar('--brand-crimson')     || '#DC2626',
      fallback:      getCSSVar('--border-input')     || (theme === 'dark' ? '#3A3A3A' : '#D6D3D1'),
    };
  }, [theme]);
}
