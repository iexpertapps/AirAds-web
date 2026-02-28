import { Link } from 'react-router-dom';
import { Home } from 'lucide-react';
import styles from './NotFoundPage.module.css';

export default function NotFoundPage() {
  return (
    <div className={styles.container}>
      <div className={styles.content}>
        <h1 className={styles.code}>404</h1>
        <h2 className={styles.title}>Page not found</h2>
        <p className={styles.description}>
          The page you're looking for doesn't exist or has been moved.
        </p>
        <Link to="/" className={styles.homeLink}>
          <Home size={18} />
          Back to Home
        </Link>
      </div>
    </div>
  );
}
