import { WifiOff } from 'lucide-react';
import { useOnline } from '@/hooks/useOnline';
import styles from './OfflineBanner.module.css';

export function OfflineBanner() {
  const isOnline = useOnline();
  if (isOnline) return null;

  return (
    <div className={styles.banner} role="alert">
      <WifiOff size={16} />
      <span>You're offline. Some features may be unavailable.</span>
    </div>
  );
}
