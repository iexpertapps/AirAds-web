import styles from './TagChip.module.css';

interface TagChipProps {
  label: string;
  selected?: boolean;
  count?: number;
  onClick?: () => void;
  icon?: string | null;
  size?: 'sm' | 'md';
}

export function TagChip({
  label,
  selected = false,
  count,
  onClick,
  icon,
  size = 'md',
}: TagChipProps) {
  return (
    <button
      className={`${styles.chip} ${selected ? styles.selected : ''} ${styles[size]}`}
      onClick={onClick}
      type="button"
      role="option"
      aria-selected={selected}
    >
      {icon && <span className={styles.icon}>{icon}</span>}
      <span className={styles.label}>{label}</span>
      {count !== undefined && (
        <span className={styles.count}>{count}</span>
      )}
    </button>
  );
}
