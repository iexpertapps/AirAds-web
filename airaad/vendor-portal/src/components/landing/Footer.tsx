import { Link } from 'react-router-dom';
import styles from './Footer.module.css';

export function Footer() {
  const year = new Date().getFullYear();

  return (
    <footer className={styles.footer}>
      <div className={styles.inner}>
        <div className={styles.brandCol}>
          <div className={styles.brandLogo}>
            <img src="/airad_icon.png" alt="AirAd" className={styles.brandIcon} />
            <span className={styles.brandName}>AirAd</span>
          </div>
          <p className={styles.brandTagline}>
            Your business, discovered by everyone nearby through augmented reality.
          </p>
        </div>

        <div>
          <h3 className={styles.colHeading}>Product</h3>
          <ul className={styles.linkList}>
            <li><a href="#how-it-works" className={styles.link}>How It Works</a></li>
            <li><a href="#pricing" className={styles.link}>Pricing</a></li>
            <li><Link to="/login" className={styles.link}>Vendor Login</Link></li>
          </ul>
        </div>

        <div>
          <h3 className={styles.colHeading}>Support</h3>
          <ul className={styles.linkList}>
            <li><a href="mailto:support@airad.pk" className={styles.link}>Contact Us</a></li>
            <li><a href="#faq" className={styles.link}>FAQ</a></li>
          </ul>
        </div>

        <div>
          <h3 className={styles.colHeading}>Legal</h3>
          <ul className={styles.linkList}>
            <li><a href="/privacy" className={styles.link}>Privacy Policy</a></li>
            <li><a href="/terms" className={styles.link}>Terms of Service</a></li>
          </ul>
        </div>
      </div>

      <div className={styles.bottom}>
        <span className={styles.copyright}>&copy; {year} AirAd. All rights reserved.</span>
      </div>
    </footer>
  );
}
