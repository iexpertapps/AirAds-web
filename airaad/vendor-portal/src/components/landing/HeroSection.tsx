import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ChevronDown } from 'lucide-react';
import styles from './HeroSection.module.css';

function ARMockup() {
  return (
    <svg viewBox="0 0 960 440" fill="none" xmlns="http://www.w3.org/2000/svg" className={styles.mockupSvg}>
      <rect width="960" height="440" fill="#0C0C1A" />
      <rect width="960" height="440" fill="url(#arStreet)" opacity="0.4" />
      {/* Road lines */}
      <line x1="0" y1="360" x2="960" y2="360" stroke="#222" strokeWidth="1" />
      <line x1="200" y1="360" x2="480" y2="440" stroke="#333" strokeWidth="1" strokeDasharray="8 6" />
      <line x1="760" y1="360" x2="480" y2="440" stroke="#333" strokeWidth="1" strokeDasharray="8 6" />
      {/* Building silhouettes */}
      <rect x="40" y="200" width="120" height="160" rx="4" fill="#151525" />
      <rect x="50" y="220" width="20" height="20" rx="2" fill="#1a1a2e" />
      <rect x="80" y="220" width="20" height="20" rx="2" fill="#1a1a2e" />
      <rect x="110" y="220" width="20" height="20" rx="2" fill="#1a1a2e" />
      <rect x="50" y="260" width="20" height="20" rx="2" fill="#1a1a2e" />
      <rect x="80" y="260" width="20" height="20" rx="2" fill="#1a1a2e" />
      <rect x="110" y="260" width="20" height="20" rx="2" fill="#1a1a2e" />
      <rect x="800" y="180" width="130" height="180" rx="4" fill="#151525" />
      <rect x="810" y="200" width="22" height="20" rx="2" fill="#1a1a2e" />
      <rect x="840" y="200" width="22" height="20" rx="2" fill="#1a1a2e" />
      <rect x="870" y="200" width="22" height="20" rx="2" fill="#1a1a2e" />
      <rect x="810" y="240" width="22" height="20" rx="2" fill="#1a1a2e" />
      <rect x="840" y="240" width="22" height="20" rx="2" fill="#1a1a2e" />
      <rect x="870" y="240" width="22" height="20" rx="2" fill="#1a1a2e" />
      {/* Vendor bubble 1 — left */}
      <circle cx="240" cy="160" r="60" fill="#F97316" opacity="0.08" />
      <circle cx="240" cy="160" r="44" stroke="#F97316" strokeWidth="2" opacity="0.5" />
      <rect x="196" y="138" width="88" height="44" rx="10" fill="#F97316" />
      <text x="240" y="157" textAnchor="middle" fill="#fff" fontSize="13" fontWeight="700" fontFamily="DM Sans,sans-serif">20% OFF</text>
      <text x="240" y="172" textAnchor="middle" fill="rgba(255,255,255,0.7)" fontSize="9" fontFamily="DM Sans,sans-serif">Burger Lab</text>
      <line x1="240" y1="204" x2="240" y2="240" stroke="#F97316" strokeWidth="1.5" strokeDasharray="4 3" />
      <circle cx="240" cy="248" r="5" fill="#F97316" />
      {/* Vendor bubble 2 — center */}
      <circle cx="480" cy="120" r="72" fill="#F97316" opacity="0.06" />
      <circle cx="480" cy="120" r="54" stroke="#F97316" strokeWidth="2.5" opacity="0.6" />
      <rect x="420" y="92" width="120" height="56" rx="12" fill="#F97316" />
      <text x="480" y="114" textAnchor="middle" fill="#fff" fontSize="11" fontWeight="700" fontFamily="DM Sans,sans-serif">Pizza Hub</text>
      <text x="480" y="130" textAnchor="middle" fill="rgba(255,255,255,0.8)" fontSize="10" fontFamily="DM Sans,sans-serif">★ 4.8 · 50m away</text>
      <line x1="480" y1="174" x2="480" y2="220" stroke="#F97316" strokeWidth="1.5" strokeDasharray="4 3" />
      <circle cx="480" cy="228" r="6" fill="#F97316" />
      {/* Vendor bubble 3 — right */}
      <circle cx="720" cy="150" r="52" fill="#0D9488" opacity="0.08" />
      <circle cx="720" cy="150" r="38" stroke="#0D9488" strokeWidth="2" opacity="0.5" />
      <rect x="682" y="132" width="76" height="36" rx="8" fill="#0D9488" />
      <text x="720" y="155" textAnchor="middle" fill="#fff" fontSize="12" fontWeight="700" fontFamily="DM Sans,sans-serif">OPEN</text>
      <line x1="720" y1="188" x2="720" y2="218" stroke="#0D9488" strokeWidth="1.5" strokeDasharray="4 3" />
      <circle cx="720" cy="225" r="4.5" fill="#0D9488" />
      {/* Camera UI chrome */}
      <rect x="24" y="20" width="100" height="12" rx="6" fill="rgba(255,255,255,0.1)" />
      <circle cx="920" cy="26" r="12" stroke="rgba(255,255,255,0.15)" strokeWidth="1.5" fill="none" />
      <circle cx="920" cy="26" r="5" fill="rgba(255,255,255,0.08)" />
      <rect x="24" y="400" width="160" height="24" rx="12" fill="rgba(255,255,255,0.06)" />
      <text x="104" y="416" textAnchor="middle" fill="rgba(255,255,255,0.4)" fontSize="10" fontFamily="DM Sans,sans-serif">3 vendors nearby</text>
      <defs>
        <linearGradient id="arStreet" x1="0" y1="0" x2="960" y2="440">
          <stop offset="0%" stopColor="#1a1a2e" />
          <stop offset="100%" stopColor="#16213e" />
        </linearGradient>
      </defs>
    </svg>
  );
}

function DashboardMockup() {
  return (
    <svg viewBox="0 0 960 440" fill="none" xmlns="http://www.w3.org/2000/svg" className={styles.mockupSvg}>
      <rect width="960" height="440" fill="#0F0F0F" />
      {/* Header */}
      <rect x="32" y="24" width="100" height="14" rx="6" fill="#F97316" />
      <text x="32" y="64" fill="rgba(255,255,255,0.45)" fontSize="12" fontFamily="DM Sans,sans-serif">Today's Performance</text>
      {/* 4 KPI cards */}
      {[0, 1, 2, 3].map((i) => (
        <g key={i} transform={`translate(${32 + i * 228}, 80)`}>
          <rect width="210" height="80" rx="12" fill="#1A1A1A" stroke="#2A2A2A" strokeWidth="1" />
          <text x="20" y="30" fill="rgba(255,255,255,0.4)" fontSize="11" fontFamily="DM Sans,sans-serif">
            {['Views', 'AR Taps', 'Nav Clicks', 'Revenue'][i]}
          </text>
          <text x="20" y="60" fill="#F5F5F4" fontSize="24" fontWeight="700" fontFamily="DM Sans,sans-serif">
            {['1,247', '389', '67', 'PKR 12K'][i]}
          </text>
        </g>
      ))}
      {/* Chart area */}
      <text x="32" y="200" fill="rgba(255,255,255,0.45)" fontSize="12" fontFamily="DM Sans,sans-serif">Views — Last 7 Days</text>
      <line x1="32" y1="400" x2="928" y2="400" stroke="#1E1E1E" strokeWidth="1" />
      {['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].map((d, i) => (
        <text key={d} x={32 + i * 132 + 66} y="420" textAnchor="middle" fill="rgba(255,255,255,0.25)" fontSize="10" fontFamily="DM Sans,sans-serif">{d}</text>
      ))}
      <polyline points="32,380 160,340 290,350 420,290 550,310 680,270 810,250 928,265" fill="none" stroke="#F97316" strokeWidth="2.5" />
      <polyline points="32,380 160,340 290,350 420,290 550,310 680,270 810,250 928,265 928,400 32,400" fill="url(#dashChart)" opacity="0.15" />
      {[32, 160, 290, 420, 550, 680, 810, 928].map((x, i) => (
        <circle key={i} cx={x} cy={[380, 340, 350, 290, 310, 270, 250, 265][i]} r="4" fill="#F97316" />
      ))}
      <defs>
        <linearGradient id="dashChart" x1="480" y1="240" x2="480" y2="400">
          <stop offset="0%" stopColor="#F97316" />
          <stop offset="100%" stopColor="transparent" />
        </linearGradient>
      </defs>
    </svg>
  );
}

function DiscountMockup() {
  return (
    <svg viewBox="0 0 960 440" fill="none" xmlns="http://www.w3.org/2000/svg" className={styles.mockupSvg}>
      <rect width="960" height="440" fill="#0A0A0A" />
      <rect width="960" height="440" fill="url(#discGrad)" opacity="0.3" />
      {/* Main discount card — center */}
      <rect x="280" y="40" width="400" height="360" rx="24" fill="#161616" stroke="#2A2A2A" strokeWidth="1" />
      <circle cx="480" cy="120" r="40" fill="#F97316" opacity="0.12" />
      <text x="480" y="130" textAnchor="middle" fill="#F97316" fontSize="32" fontWeight="800" fontFamily="DM Sans,sans-serif">%</text>
      <text x="480" y="180" textAnchor="middle" fill="#F5F5F4" fontSize="22" fontWeight="700" fontFamily="DM Sans,sans-serif">Happy Hour Special</text>
      <text x="480" y="210" textAnchor="middle" fill="rgba(255,255,255,0.5)" fontSize="14" fontFamily="DM Sans,sans-serif">Café Bliss · Gulberg, Lahore</text>
      <rect x="380" y="240" width="200" height="56" rx="28" fill="#F97316" />
      <text x="480" y="274" textAnchor="middle" fill="#fff" fontSize="18" fontWeight="600" fontFamily="DM Sans,sans-serif">30% Off Lunch</text>
      <text x="480" y="330" textAnchor="middle" fill="rgba(255,255,255,0.3)" fontSize="12" fontFamily="DM Sans,sans-serif">Valid 12 PM — 3 PM · Tap to navigate</text>
      <rect x="400" y="355" width="160" height="28" rx="14" fill="rgba(255,255,255,0.06)" />
      <text x="480" y="374" textAnchor="middle" fill="rgba(255,255,255,0.4)" fontSize="11" fontFamily="DM Sans,sans-serif">★ 4.6 · 120 reviews</text>
      {/* Side cards — left */}
      <rect x="40" y="100" width="200" height="240" rx="16" fill="#161616" stroke="#222" strokeWidth="1" opacity="0.6" />
      <circle cx="140" cy="160" r="20" fill="#0D9488" opacity="0.12" />
      <text x="140" y="166" textAnchor="middle" fill="#0D9488" fontSize="16" fontWeight="800" fontFamily="DM Sans,sans-serif">%</text>
      <text x="140" y="200" textAnchor="middle" fill="rgba(255,255,255,0.6)" fontSize="12" fontWeight="600" fontFamily="DM Sans,sans-serif">BOGO Friday</text>
      <text x="140" y="220" textAnchor="middle" fill="rgba(255,255,255,0.3)" fontSize="10" fontFamily="DM Sans,sans-serif">Spice Garden</text>
      {/* Side cards — right */}
      <rect x="720" y="100" width="200" height="240" rx="16" fill="#161616" stroke="#222" strokeWidth="1" opacity="0.6" />
      <circle cx="820" cy="160" r="20" fill="#F97316" opacity="0.12" />
      <text x="820" y="166" textAnchor="middle" fill="#F97316" fontSize="16" fontWeight="800" fontFamily="DM Sans,sans-serif">%</text>
      <text x="820" y="200" textAnchor="middle" fill="rgba(255,255,255,0.6)" fontSize="12" fontWeight="600" fontFamily="DM Sans,sans-serif">15% Off Dinner</text>
      <text x="820" y="220" textAnchor="middle" fill="rgba(255,255,255,0.3)" fontSize="10" fontFamily="DM Sans,sans-serif">The Patio</text>
      {/* Ambient */}
      <circle cx="80" cy="60" r="8" fill="#0D9488" opacity="0.2" />
      <circle cx="880" cy="380" r="10" fill="#F97316" opacity="0.15" />
      <defs>
        <linearGradient id="discGrad" x1="0" y1="0" x2="960" y2="440">
          <stop offset="0%" stopColor="#0a0a0a" />
          <stop offset="100%" stopColor="#1a0a00" />
        </linearGradient>
      </defs>
    </svg>
  );
}

const SLIDES = [
  { Mockup: ARMockup, label: 'AR camera view with vendor bubbles and live offers' },
  { Mockup: DashboardMockup, label: 'Real-time analytics dashboard for vendors' },
  { Mockup: DiscountMockup, label: 'Customer discovering a nearby discount via AR' },
] as const;

const SLIDE_INTERVAL = 5000;

export function HeroSection() {
  const [activeSlide, setActiveSlide] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setActiveSlide((prev) => (prev + 1) % SLIDES.length);
    }, SLIDE_INTERVAL);
    return () => clearInterval(timer);
  }, []);

  return (
    <section className={styles.hero} aria-label="Hero">
      {/* Full-width slides */}
      <div className={styles.slidesWrap}>
        {SLIDES.map((slide, i) => {
          const SlideComponent = slide.Mockup;
          return (
            <div
              key={i}
              className={[styles.slide, i === activeSlide ? styles['slide--active'] : ''].join(' ')}
              aria-hidden={i !== activeSlide}
              aria-label={slide.label}
            >
              <SlideComponent />
            </div>
          );
        })}
        {/* Slide indicators */}
        <div className={styles.indicators}>
          {SLIDES.map((_, i) => (
            <button
              key={i}
              className={[styles.dot, i === activeSlide ? styles['dot--active'] : ''].join(' ')}
              onClick={() => setActiveSlide(i)}
              aria-label={`Slide ${i + 1}`}
            />
          ))}
        </div>
        {/* Bottom gradient fade into content section */}
        <div className={styles.slideFade} aria-hidden="true" />
      </div>

      {/* Heading + subtext below slides */}
      <motion.div
        className={styles.content}
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, ease: [0.4, 0, 0.2, 1] }}
      >
        <h1 className={styles.headline}>
          Your Business, Discovered by Everyone Nearby
        </h1>
        <p className={styles.subheadline}>
          Customers are walking past your door right now.
          AirAd puts your business in their camera view.
        </p>
        <Link to="/onboarding/search" className={styles.ctaButton}>
          Claim Your Business — Free
        </Link>
      </motion.div>

      <div className={styles.scrollHint} aria-hidden="true">
        <span>Scroll to learn more</span>
        <ChevronDown size={20} strokeWidth={1.5} />
      </div>
    </section>
  );
}
