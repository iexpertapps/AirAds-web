import { motion } from 'framer-motion';
import { useInView } from 'react-intersection-observer';
import { MapPin, Megaphone, TrendingUp, ArrowRight } from 'lucide-react';
import CountUp from 'react-countup';
import styles from './HowItWorksSection.module.css';

const STEPS = [
  {
    number: 1,
    icon: MapPin,
    title: 'Claim',
    description: 'Find your business on AirAd and claim it for free in under 2 minutes.',
  },
  {
    number: 2,
    icon: Megaphone,
    title: 'Promote',
    description: 'Create discounts and short reels to attract customers walking nearby.',
  },
  {
    number: 3,
    icon: TrendingUp,
    title: 'Grow',
    description: 'Watch real customers discover you through AR and track every view.',
  },
] as const;

const cardVariants = {
  hidden: { opacity: 0, y: 40 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { delay: i * 0.2, duration: 0.6, ease: [0.4, 0, 0.2, 1] },
  }),
};

export function HowItWorksSection() {
  const { ref, inView } = useInView({ triggerOnce: true, threshold: 0.2 });

  return (
    <section id="how-it-works" className={styles.section} aria-label="How it works">
      <div className={styles.inner} ref={ref}>
        <h2 className={styles.heading}>How AirAd Works for You</h2>

        <div className={styles.steps}>
          {STEPS.map((step, i) => {
            const Icon = step.icon;
            return (
              <motion.div
                key={step.number}
                className={styles.stepCard}
                variants={cardVariants}
                initial="hidden"
                animate={inView ? 'visible' : 'hidden'}
                custom={i}
              >
                <div className={styles.stepNumber}>
                  {inView ? <CountUp end={step.number} duration={0.8} delay={i * 0.2} /> : step.number}
                </div>
                <div className={styles.stepIcon}>
                  <Icon size={32} strokeWidth={1.5} />
                </div>
                <h3 className={styles.stepTitle}>{step.title}</h3>
                <p className={styles.stepDesc}>{step.description}</p>
              </motion.div>
            );
          })}

          <div className={[styles.connector, styles['connector--1']].join(' ')} aria-hidden="true">
            <ArrowRight size={24} strokeWidth={1.5} />
          </div>
          <div className={[styles.connector, styles['connector--2']].join(' ')} aria-hidden="true">
            <ArrowRight size={24} strokeWidth={1.5} />
          </div>
        </div>
      </div>
    </section>
  );
}
