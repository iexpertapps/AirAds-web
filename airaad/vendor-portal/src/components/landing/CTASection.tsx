import { motion } from 'framer-motion';
import { useInView } from 'react-intersection-observer';
import { Link } from 'react-router-dom';
import styles from './CTASection.module.css';

export function CTASection() {
  const { ref, inView } = useInView({ triggerOnce: true, threshold: 0.3 });

  return (
    <section className={styles.section} aria-label="Call to action">
      <motion.div
        className={styles.inner}
        ref={ref}
        initial={{ opacity: 0, y: 20 }}
        animate={inView ? { opacity: 1, y: 0 } : { opacity: 0, y: 20 }}
        transition={{ duration: 0.6, ease: [0.4, 0, 0.2, 1] }}
      >
        <h2 className={styles.heading}>Ready to Be Discovered?</h2>
        <p className={styles.subtext}>
          Join thousands of vendors already growing their business with AirAd. It&apos;s free to start.
        </p>
        <Link to="/onboarding/search" className={styles.ctaButton}>
          Claim Your Business Now — Free
        </Link>
      </motion.div>
    </section>
  );
}
