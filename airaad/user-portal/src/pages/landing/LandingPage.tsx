import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Camera, Mic, MapPin, Star, ArrowRight, Smartphone, Menu, X } from 'lucide-react';
import { useState } from 'react';
import { Button } from '@/components/dls/Button';
import styles from './LandingPage.module.css';

const NAV_LINKS = [
  { label: 'How It Works', href: '#how-it-works' },
  { label: 'Modes', href: '#modes' },
  { label: 'For Business', href: 'https://vendor.airad.pk' },
];

function Navbar() {
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <nav className={styles.navbar}>
      <div className={styles.navInner}>
        <Link to="/" className={styles.navLogo}>
          <img src="/airad_icon.png" alt="AirAd" className={styles.navLogoImg} />
          <span className={styles.navLogoText}>AirAd</span>
        </Link>
        <div className={`${styles.navLinks} ${menuOpen ? styles.navLinksOpen : ''}`}>
          {NAV_LINKS.map((link) => (
            <a key={link.label} href={link.href} className={styles.navLink} onClick={() => setMenuOpen(false)}>
              {link.label}
            </a>
          ))}
          <Link to="/discover" className={styles.navCta} onClick={() => setMenuOpen(false)}>
            Explore Nearby
          </Link>
        </div>
        <button
          className={styles.menuToggle}
          onClick={() => setMenuOpen(!menuOpen)}
          aria-label={menuOpen ? 'Close menu' : 'Open menu'}
        >
          {menuOpen ? <X size={24} /> : <Menu size={24} />}
        </button>
      </div>
    </nav>
  );
}

function HeroSection() {
  return (
    <section className={styles.hero}>
      <div className={styles.heroOverlay} />
      <div className={styles.heroContent}>
        <motion.h1
          className={styles.heroTitle}
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
        >
          Discover Amazing Vendors{' '}
          <span className="brand-gradient-text">Right Around You</span>
        </motion.h1>
        <motion.p
          className={styles.heroSubtitle}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.2 }}
        >
          Point your camera, speak your needs, or browse the map — AirAd connects you
          to the best nearby businesses with AR, voice search, and real-time deals.
        </motion.p>
        <motion.div
          className={styles.heroCtas}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.4 }}
        >
          <Link to="/discover">
            <Button size="lg" icon={<Camera size={20} />}>
              Start Exploring
            </Button>
          </Link>
          <a href="#how-it-works">
            <Button variant="secondary" size="lg">
              See How It Works
            </Button>
          </a>
        </motion.div>
        <motion.div
          className={styles.heroStats}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.6, delay: 0.6 }}
        >
          <div className={styles.heroStat}>
            <span className={styles.heroStatNum}>500+</span>
            <span className={styles.heroStatLabel}>Vendors</span>
          </div>
          <div className={styles.heroStat}>
            <span className={styles.heroStatNum}>15+</span>
            <span className={styles.heroStatLabel}>Cities</span>
          </div>
          <div className={styles.heroStat}>
            <span className={styles.heroStatNum}>4.8</span>
            <span className={styles.heroStatLabel}>
              <Star size={12} /> Rating
            </span>
          </div>
        </motion.div>
      </div>
    </section>
  );
}

const HOW_IT_WORKS = [
  {
    step: '01',
    icon: <Smartphone size={32} />,
    title: 'Open AirAd',
    description: 'No signup required. Start discovering vendors instantly as a guest.',
  },
  {
    step: '02',
    icon: <Camera size={32} />,
    title: 'Choose Your Mode',
    description: 'AR camera view, interactive map, or scrollable list — pick what suits you.',
  },
  {
    step: '03',
    icon: <Star size={32} />,
    title: 'Discover & Visit',
    description: 'Find deals, watch reels, get directions, and visit amazing local vendors.',
  },
];

function HowItWorksSection() {
  return (
    <section id="how-it-works" className={styles.howItWorks}>
      <div className={styles.sectionInner}>
        <h2 className={styles.sectionTitle}>How It Works</h2>
        <p className={styles.sectionSubtitle}>Three simple steps to discover nearby vendors</p>
        <div className={styles.stepsGrid}>
          {HOW_IT_WORKS.map((item, i) => (
            <motion.div
              key={item.step}
              className={styles.stepCard}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.15 }}
            >
              <span className={styles.stepNum}>{item.step}</span>
              <div className={styles.stepIcon}>{item.icon}</div>
              <h3 className={styles.stepTitle}>{item.title}</h3>
              <p className={styles.stepDesc}>{item.description}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}

const MODES = [
  {
    icon: <Camera size={40} />,
    title: 'AR Discovery',
    description: 'Point your camera and see vendor markers floating in the real world. Tap to explore deals, reels, and profiles.',
    color: 'var(--brand-orange)',
  },
  {
    icon: <Mic size={40} />,
    title: 'Voice Search',
    description: '"Find a coffee shop nearby with deals" — just speak naturally and let AirAd understand your intent.',
    color: 'var(--brand-crimson)',
  },
  {
    icon: <MapPin size={40} />,
    title: 'Map & List',
    description: 'Browse an interactive map with vendor pins or scroll through a curated list sorted by relevance.',
    color: 'var(--brand-teal)',
  },
];

function ModesSection() {
  return (
    <section id="modes" className={styles.modes}>
      <div className={styles.sectionInner}>
        <h2 className={styles.sectionTitle}>Three Ways to Discover</h2>
        <p className={styles.sectionSubtitle}>Choose the experience that fits your moment</p>
        <div className={styles.modesGrid}>
          {MODES.map((mode, i) => (
            <motion.div
              key={mode.title}
              className={styles.modeCard}
              initial={{ opacity: 0, scale: 0.95 }}
              whileInView={{ opacity: 1, scale: 1 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.15 }}
            >
              <div className={styles.modeIcon} style={{ color: mode.color }}>
                {mode.icon}
              </div>
              <h3 className={styles.modeTitle}>{mode.title}</h3>
              <p className={styles.modeDesc}>{mode.description}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}

function CTASection() {
  return (
    <section className={styles.cta}>
      <div className={styles.sectionInner}>
        <motion.div
          className={styles.ctaContent}
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
        >
          <h2 className={styles.ctaTitle}>Ready to Discover?</h2>
          <p className={styles.ctaSubtitle}>
            No account needed. Start exploring vendors around you right now.
          </p>
          <Link to="/discover">
            <Button size="lg" icon={<ArrowRight size={20} />}>
              Start Exploring Now
            </Button>
          </Link>
        </motion.div>
      </div>
    </section>
  );
}

function Footer() {
  return (
    <footer className={styles.footer}>
      <div className={styles.footerInner}>
        <div className={styles.footerBrand}>
          <img src="/airad_icon.png" alt="AirAd" className={styles.footerLogo} />
          <span className={styles.footerBrandName}>AirAd</span>
        </div>
        <div className={styles.footerLinks}>
          <Link to="/discover">Discover</Link>
          <a href="https://vendor.airad.pk">For Business</a>
        </div>
        <p className={styles.footerCopy}>© {new Date().getFullYear()} AirAd. All rights reserved.</p>
      </div>
    </footer>
  );
}

export default function LandingPage() {
  return (
    <div className={styles.page}>
      <Navbar />
      <main id="main-content">
        <HeroSection />
        <HowItWorksSection />
        <ModesSection />
        <CTASection />
      </main>
      <Footer />
    </div>
  );
}
