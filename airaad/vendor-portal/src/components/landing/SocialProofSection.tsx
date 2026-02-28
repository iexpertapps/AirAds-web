import { motion } from 'framer-motion';
import { useInView } from 'react-intersection-observer';
import { useQuery } from '@tanstack/react-query';
import CountUp from 'react-countup';
import { getLandingStats } from '@/api/landing';
import styles from './SocialProofSection.module.css';

const FALLBACK_STATS = [
  { value: 2500, suffix: '+', label: 'Active Vendors' },
  { value: 15, suffix: '+', label: 'Cities Covered' },
  { value: 50000, suffix: '+', label: 'Monthly AR Views' },
];

const TESTIMONIALS = [
  {
    quote: 'Since joining AirAd, my daily walk-ins increased by 40%. The AR discovery is game-changing for small shops.',
    name: 'Ahmad',
    business: 'Pizza Hub, F-10 Islamabad',
    initials: 'AH',
  },
  {
    quote: 'I was skeptical about AR, but the analytics don\'t lie. My Gold subscription paid for itself in the first week.',
    name: 'Fatima',
    business: 'Café Bliss, Gulberg Lahore',
    initials: 'FB',
  },
  {
    quote: 'The claim process took 2 minutes. Now customers find me through their camera instead of Google Maps.',
    name: 'Hassan',
    business: 'Quick Mart, DHA Karachi',
    initials: 'HK',
  },
] as const;

const cardVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { delay: i * 0.15, duration: 0.5, ease: [0.4, 0, 0.2, 1] },
  }),
};

export function SocialProofSection() {
  const { ref, inView } = useInView({ triggerOnce: true, threshold: 0.2 });

  const { data: apiStats } = useQuery({
    queryKey: ['landing-stats'],
    queryFn: getLandingStats,
    staleTime: 300_000,
  });

  const stats = apiStats
    ? [
        { value: apiStats.total_active_vendors ?? 0, suffix: '+', label: 'Active Vendors' },
        { value: apiStats.total_cities ?? 0, suffix: '+', label: 'Cities Covered' },
        { value: apiStats.avg_views_after_claim ?? 0, suffix: '+', label: 'Monthly AR Views' },
      ]
    : FALLBACK_STATS;

  return (
    <section className={styles.section} aria-label="Social proof">
      <div className={styles.inner} ref={ref}>
        <h2 className={styles.heading}>Trusted by Vendors Across Pakistan</h2>

        <div className={styles.statsRow}>
          {stats.map((stat, i) => (
            <motion.div
              key={stat.label}
              className={styles.statCard}
              variants={cardVariants}
              initial="hidden"
              animate={inView ? 'visible' : 'hidden'}
              custom={i}
            >
              <span className={styles.statValue}>
                {inView ? (
                  <CountUp end={stat.value} duration={2} delay={i * 0.2} separator="," suffix={stat.suffix} />
                ) : (
                  `${stat.value.toLocaleString()}${stat.suffix}`
                )}
              </span>
              <span className={styles.statLabel}>{stat.label}</span>
            </motion.div>
          ))}
        </div>

        <div className={styles.testimonials}>
          {TESTIMONIALS.map((t, i) => (
            <motion.div
              key={t.name}
              className={styles.testimonialCard}
              variants={cardVariants}
              initial="hidden"
              animate={inView ? 'visible' : 'hidden'}
              custom={i + stats.length}
            >
              <p className={styles.quoteText}>{t.quote}</p>
              <div className={styles.authorRow}>
                <div className={styles.authorAvatar}>{t.initials}</div>
                <div className={styles.authorInfo}>
                  <span className={styles.authorName}>{t.name}</span>
                  <span className={styles.authorBiz}>{t.business}</span>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
