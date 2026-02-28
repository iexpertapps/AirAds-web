import { motion } from 'framer-motion';
import { useInView } from 'react-intersection-observer';
import { Link } from 'react-router-dom';
import { Check, X } from 'lucide-react';
import CountUp from 'react-countup';
import styles from './TierPreviewSection.module.css';

interface TierFeature {
  label: string;
  included: boolean;
}

interface Tier {
  name: string;
  price: number;
  unit: string;
  popular: boolean;
  features: TierFeature[];
  ctaLabel: string;
  ctaTo: string;
}

const TIERS: Tier[] = [
  {
    name: 'Silver',
    price: 0,
    unit: 'Free forever',
    popular: false,
    features: [
      { label: '1 reel upload', included: true },
      { label: 'Basic AR visibility', included: true },
      { label: 'Basic metrics', included: true },
      { label: 'Voice introduction', included: false },
      { label: 'Happy hour discounts', included: false },
      { label: 'Verified badge', included: false },
    ],
    ctaLabel: 'Claim Free',
    ctaTo: '/onboarding/search',
  },
  {
    name: 'Gold',
    price: 3000,
    unit: '/month',
    popular: false,
    features: [
      { label: '3 reel uploads', included: true },
      { label: 'Boosted AR ranking', included: true },
      { label: 'Voice introduction', included: true },
      { label: 'Verified badge', included: true },
      { label: '1 happy hour/day', included: true },
      { label: 'Dynamic voice bot', included: false },
    ],
    ctaLabel: 'Upgrade Now',
    ctaTo: '/portal/subscription',
  },
  {
    name: 'Diamond',
    price: 7000,
    unit: '/month',
    popular: true,
    features: [
      { label: '6 reel uploads', included: true },
      { label: 'High priority AR', included: true },
      { label: 'Dynamic voice bot', included: true },
      { label: 'Premium badge', included: true },
      { label: '3 happy hours/day', included: true },
      { label: 'Advanced analytics', included: true },
    ],
    ctaLabel: 'Upgrade Now',
    ctaTo: '/portal/subscription',
  },
  {
    name: 'Platinum',
    price: 15000,
    unit: '/month',
    popular: false,
    features: [
      { label: 'Unlimited reels', included: true },
      { label: 'Dominant zone AR', included: true },
      { label: 'Advanced voice bot', included: true },
      { label: 'Elite crown badge', included: true },
      { label: 'Smart automation', included: true },
      { label: 'Competitor insights', included: true },
    ],
    ctaLabel: 'Upgrade Now',
    ctaTo: '/portal/subscription',
  },
];

const cardVariants = {
  hidden: { opacity: 0, y: 30 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { delay: i * 0.15, duration: 0.5, ease: [0.4, 0, 0.2, 1] },
  }),
};

export function TierPreviewSection() {
  const { ref, inView } = useInView({ triggerOnce: true, threshold: 0.15 });

  return (
    <section id="pricing" className={styles.section} aria-label="Pricing tiers">
      <div className={styles.inner} ref={ref}>
        <h2 className={styles.heading}>Choose Your Visibility Level</h2>
        <p className={styles.subheading}>
          Start free, upgrade when you&apos;re ready to dominate your area.
        </p>

        <div className={styles.grid}>
          {TIERS.map((tier, i) => (
            <motion.div
              key={tier.name}
              className={[styles.card, tier.popular ? styles['card--popular'] : ''].join(' ')}
              variants={cardVariants}
              initial="hidden"
              animate={inView ? 'visible' : 'hidden'}
              custom={i}
            >
              {tier.popular && (
                <span className={styles.popularBadge}>Most Popular</span>
              )}

              <span className={styles.tierName}>{tier.name}</span>

              <div className={styles.priceRow}>
                {tier.price === 0 ? (
                  <span className={styles.freeLabel}>Free</span>
                ) : (
                  <>
                    <span className={styles.currency}>PKR</span>
                    <span className={styles.priceValue}>
                      {inView ? (
                        <CountUp end={tier.price} duration={1.2} delay={i * 0.15} separator="," />
                      ) : (
                        tier.price.toLocaleString()
                      )}
                    </span>
                    <span className={styles.priceUnit}>{tier.unit}</span>
                  </>
                )}
              </div>

              <ul className={styles.features}>
                {tier.features.map((feat) => (
                  <li key={feat.label} className={styles.featureItem}>
                    {feat.included ? (
                      <Check size={16} strokeWidth={2} className={styles['featureIcon--check']} aria-label="Included" />
                    ) : (
                      <X size={16} strokeWidth={2} className={styles['featureIcon--x']} aria-label="Not included" />
                    )}
                    {feat.label}
                  </li>
                ))}
              </ul>

              <Link
                to={tier.ctaTo}
                className={[
                  styles.ctaButton,
                  tier.popular ? styles['ctaButton--primary'] : styles['ctaButton--secondary'],
                ].join(' ')}
              >
                {tier.ctaLabel}
              </Link>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
