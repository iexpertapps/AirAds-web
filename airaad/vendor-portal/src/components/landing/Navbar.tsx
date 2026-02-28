import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { Menu, X } from 'lucide-react';
import styles from './Navbar.module.css';

export function Navbar() {
  const [scrolled, setScrolled] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 40);
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  const closeMobile = useCallback(() => setMobileOpen(false), []);

  const variant = scrolled ? styles['navbar--solid'] : styles['navbar--transparent'];

  return (
    <>
      <nav className={[styles.navbar, variant].join(' ')} aria-label="Main navigation">
        <Link to="/" className={styles.logo} onClick={closeMobile}>
          <img src="/airad_icon.png" alt="AirAd" className={styles.logoIcon} />
          <span className={styles.logoText}>AirAd</span>
        </Link>

        <ul className={styles.navLinks}>
          <li>
            <a href="#how-it-works" className={styles.navLink}>How It Works</a>
          </li>
          <li>
            <a href="#pricing" className={styles.navLink}>Pricing</a>
          </li>
          <li>
            <Link to="/login" className={styles.ctaButton}>
              Login
            </Link>
          </li>
        </ul>

        <button
          className={styles.mobileToggle}
          onClick={() => setMobileOpen((prev) => !prev)}
          aria-label={mobileOpen ? 'Close menu' : 'Open menu'}
          aria-expanded={mobileOpen}
        >
          {mobileOpen ? <X size={24} strokeWidth={1.5} /> : <Menu size={24} strokeWidth={1.5} />}
        </button>
      </nav>

      {mobileOpen && (
        <div className={styles.mobileMenu} role="navigation" aria-label="Mobile navigation">
          <a href="#how-it-works" className={styles.mobileLink} onClick={closeMobile}>
            How It Works
          </a>
          <a href="#pricing" className={styles.mobileLink} onClick={closeMobile}>
            Pricing
          </a>
          <Link to="/login" className={styles.mobileCta} onClick={closeMobile}>
            Login
          </Link>
        </div>
      )}
    </>
  );
}
