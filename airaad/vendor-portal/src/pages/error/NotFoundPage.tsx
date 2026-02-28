import { Link } from 'react-router-dom';
import styles from './NotFoundPage.module.css';

export default function NotFoundPage() {
  return (
    <div className={styles.page}>
      <div className={styles.card}>
        <img src="/airad_icon.png" alt="AirAd" className={styles.logoIcon} />
        <h1 className={styles.code}>404</h1>
        <h2 className={styles.heading}>Page not found</h2>
        <p className={styles.subtext}>
          The page you&apos;re looking for doesn&apos;t exist or has been moved.
        </p>
        <Link to="/" className={styles.ctaButton}>
          Go to Home
        </Link>
      </div>
    </div>
  );
}
