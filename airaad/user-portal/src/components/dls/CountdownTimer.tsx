import { useState, useEffect, useCallback } from 'react';
import styles from './CountdownTimer.module.css';

interface CountdownTimerProps {
  endDate: string;
  onExpire?: () => void;
  size?: 'sm' | 'md';
  className?: string;
}

interface TimeLeft {
  hours: number;
  minutes: number;
  seconds: number;
  expired: boolean;
}

function calcTimeLeft(endDate: string): TimeLeft {
  const diff = new Date(endDate).getTime() - Date.now();
  if (diff <= 0) return { hours: 0, minutes: 0, seconds: 0, expired: true };
  return {
    hours: Math.floor(diff / 3600000),
    minutes: Math.floor((diff % 3600000) / 60000),
    seconds: Math.floor((diff % 60000) / 1000),
    expired: false,
  };
}

export function CountdownTimer({ endDate, onExpire, size = 'md', className = '' }: CountdownTimerProps) {
  const [timeLeft, setTimeLeft] = useState(() => calcTimeLeft(endDate));

  const handleTick = useCallback(() => {
    const next = calcTimeLeft(endDate);
    setTimeLeft(next);
    if (next.expired && onExpire) onExpire();
  }, [endDate, onExpire]);

  useEffect(() => {
    const id = setInterval(handleTick, 1000);
    return () => clearInterval(id);
  }, [handleTick]);

  if (timeLeft.expired) {
    return <span className={`${styles.expired} ${styles[size]} ${className}`}>Expired</span>;
  }

  const pad = (n: number) => n.toString().padStart(2, '0');

  return (
    <span className={`${styles.timer} ${styles[size]} ${className}`} aria-live="polite">
      {timeLeft.hours > 0 && <span className={styles.segment}>{pad(timeLeft.hours)}h</span>}
      <span className={styles.segment}>{pad(timeLeft.minutes)}m</span>
      <span className={styles.segment}>{pad(timeLeft.seconds)}s</span>
    </span>
  );
}
