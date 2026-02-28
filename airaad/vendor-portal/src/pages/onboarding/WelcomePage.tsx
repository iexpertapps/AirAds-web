import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { CheckCircle } from 'lucide-react';
import styles from './WelcomePage.module.css';

const FEATURES = [
  'Track views and analytics in real time',
  'Create discounts to attract nearby customers',
  'Upload short reels to showcase your business',
] as const;

export default function WelcomePage() {
  return (
    <div className={styles.page}>
      <motion.div
        className={styles.card}
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease: [0.4, 0, 0.2, 1] }}
      >
        <img src="/airad_icon.png" alt="AirAd" className={styles.logoIcon} />

        <h1 className={styles.heading}>You&apos;re All Set!</h1>
        <p className={styles.subtext}>
          Your business is now on AirAd. Customers nearby can discover you through
          augmented reality. Here&apos;s what you can do next:
        </p>

        <ul className={styles.featureList}>
          {FEATURES.map((feat) => (
            <li key={feat} className={styles.featureItem}>
              <CheckCircle size={18} strokeWidth={1.5} className={styles.featureIcon} />
              <span>{feat}</span>
            </li>
          ))}
        </ul>

        <Link to="/portal/dashboard" className={styles.ctaButton}>
          Go to Dashboard
        </Link>
      </motion.div>
    </div>
  );
}
