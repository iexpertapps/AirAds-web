import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { 
  ArrowLeft, 
  MapPin, 
  Phone, 
  Clock, 
  Star, 
  Heart, 
  Share2, 
  Navigation,
  Camera,
  Tag,
  ExternalLink,
  Film,
  Globe
} from 'lucide-react';
import { getVendorDetail, getVendorReels, getSimilarVendors } from '@/api/vendor';
import { getDealDetail } from '@/api/deals';
import { queryKeys } from '@/queryKeys';
import { formatDistance, formatRating } from '@/utils/formatters';
import { CountdownTimer } from '@/components/dls/CountdownTimer';
import { TierBadge } from '@/components/dls/TierBadge';
import { TagChip } from '@/components/dls/TagChip';
import { VendorCard } from '@/components/dls/VendorCard';
import { Skeleton } from '@/components/dls/SkeletonLoader';
import { recordInteraction } from '@/api/navigation';
import styles from './VendorProfilePage.module.css';

export default function VendorProfilePage() {
  const { vendorId } = useParams<{ vendorId: string }>();

  const {
    data: vendorRes,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: queryKeys.vendor.detail(vendorId!),
    queryFn: () => getVendorDetail(vendorId!),
    enabled: !!vendorId,
    staleTime: 5 * 60 * 1000,
  });

  const { data: reelsRes } = useQuery({
    queryKey: queryKeys.vendor.reels(vendorId!),
    queryFn: () => getVendorReels(vendorId!),
    enabled: !!vendorId,
    staleTime: 5 * 60 * 1000,
  });

  const { data: similarRes } = useQuery({
    queryKey: queryKeys.vendor.similar(vendorId!),
    queryFn: () => getSimilarVendors(vendorId!),
    enabled: !!vendorId,
    staleTime: 10 * 60 * 1000,
  });

  const { data: dealsRes } = useQuery({
    queryKey: queryKeys.deals.detail(vendorId!),
    queryFn: () => getDealDetail(vendorId!),
    enabled: !!vendorId,
    staleTime: 5 * 60 * 1000,
  });

  const vendor = vendorRes?.data;
  const reels = reelsRes?.data ?? [];
  const similar = similarRes?.data ?? [];
  const vendorDeals = dealsRes?.data ? [dealsRes.data] : [];

  const handleCall = () => {
    if (vendor?.phone) {
      recordInteraction(vendorId!, 'call');
      window.open(`tel:${vendor.phone}`, '_self');
    }
  };

  const handleShare = async () => {
    if (navigator.share && vendor) {
      try {
        await navigator.share({
          title: vendor.business_name,
          text: `Check out ${vendor.business_name} on AirAd`,
          url: window.location.href,
        });
        recordInteraction(vendorId!, 'share');
      } catch {
        // user cancelled
      }
    }
  };

  const todayKey = new Date().toLocaleDateString('en-US', { weekday: 'long' }).toLowerCase();

  if (isLoading) {
    return (
      <div className={styles.page}>
        <header className={styles.topBar}>
          <Link to="/discover" className={styles.backBtn} aria-label="Back to discover">
            <ArrowLeft size={20} />
          </Link>
          <h1 className={styles.title}>Loading…</h1>
        </header>
        <main className={styles.content} id="main-content">
          <Skeleton height="200px" />
          <div className={styles.skeletonBody}>
            <Skeleton height="24px" width="60%" />
            <Skeleton height="16px" width="40%" />
            <Skeleton height="80px" />
          </div>
        </main>
      </div>
    );
  }

  if (error || !vendor) {
    return (
      <div className={styles.page}>
        <header className={styles.topBar}>
          <Link to="/discover" className={styles.backBtn} aria-label="Back to discover">
            <ArrowLeft size={20} />
          </Link>
          <h1 className={styles.title}>Vendor Profile</h1>
        </header>
        <main className={styles.content} id="main-content">
          <div className={styles.errorState}>
            <h2>Vendor not found</h2>
            <p>Unable to load vendor information. Please try again.</p>
            <button onClick={() => refetch()} className={styles.retryBtn}>
              Retry
            </button>
          </div>
        </main>
      </div>
    );
  }

  const todayHours = vendor.business_hours?.[todayKey];

  return (
    <div className={styles.page}>
      <header className={styles.topBar}>
        <Link to="/discover" className={styles.backBtn} aria-label="Back to discover">
          <ArrowLeft size={20} />
        </Link>
        <h1 className={styles.title}>{vendor.business_name}</h1>
      </header>
      
      <main className={styles.content} id="main-content">
        {/* Hero Section */}
        <section className={styles.hero}>
          <div className={styles.heroImage}>
            {vendor.cover_url ? (
              <img src={vendor.cover_url} alt={vendor.business_name} />
            ) : (
              <div className={styles.imagePlaceholder}>
                <Camera size={48} />
              </div>
            )}
            <div className={styles.heroOverlay}>
              <div className={styles.vendorLogo}>
                {vendor.logo_url ? (
                  <img src={vendor.logo_url} alt={vendor.business_name} />
                ) : (
                  <div className={styles.logoPlaceholder}>
                    {vendor.business_name.charAt(0)}
                  </div>
                )}
              </div>
            </div>
          </div>
          
          <div className={styles.heroInfo}>
            <div className={styles.titleRow}>
              <h2 className={styles.vendorName}>{vendor.business_name}</h2>
              <TierBadge tier={vendor.subscription_tier} />
            </div>
            
            <div className={styles.metaRow}>
              <div className={styles.rating}>
                <Star size={16} className={styles.starIcon} />
                <span>{formatRating(vendor.average_rating)}</span>
                <span className={styles.reviewCount}>({vendor.review_count} reviews)</span>
              </div>
              <div className={styles.category}>{vendor.category}</div>
            </div>
            
            <p className={styles.description}>{vendor.description}</p>
            
            {vendor.has_active_promotion && vendor.active_promotion_headline && (
              <div className={styles.promotionSection}>
                <span className={styles.promoBadge}>{vendor.active_promotion_headline}</span>
              </div>
            )}
          </div>
        </section>

        {/* Action Buttons */}
        <section className={styles.actions}>
          <Link to={`/navigate/${vendor.id}`} className={styles.primaryBtn}>
            <Navigation size={18} />
            Directions
          </Link>
          {vendor.phone && (
            <button className={styles.secondaryBtn} onClick={handleCall}>
              <Phone size={18} />
              Call
            </button>
          )}
          <button className={styles.secondaryBtn}>
            <Heart size={18} />
            Save
          </button>
          <button className={styles.secondaryBtn} onClick={handleShare}>
            <Share2 size={18} />
            Share
          </button>
        </section>

        {/* Quick Info */}
        <section className={styles.quickInfo}>
          <div className={styles.infoCard}>
            <MapPin size={20} className={styles.infoIcon} />
            <div className={styles.infoContent}>
              <h3>Location</h3>
              <p>{vendor.address}, {vendor.area}, {vendor.city}</p>
              <span className={styles.distance}>{formatDistance(vendor.distance_km)} away</span>
            </div>
          </div>
          
          <div className={styles.infoCard}>
            <Clock size={20} className={styles.infoIcon} />
            <div className={styles.infoContent}>
              <h3>Hours</h3>
              <p className={vendor.is_open ? styles.openStatus : styles.closedStatus}>
                {vendor.is_open ? 'Open now' : 'Closed'}
              </p>
              {todayHours && (
                <span className={styles.hours}>{todayHours.open} – {todayHours.close}</span>
              )}
            </div>
          </div>
          
          {(vendor.phone || vendor.website) && (
            <div className={styles.infoCard}>
              <Globe size={20} className={styles.infoIcon} />
              <div className={styles.infoContent}>
                <h3>Contact</h3>
                {vendor.phone && <p>{vendor.phone}</p>}
                {vendor.website && (
                  <a href={vendor.website} target="_blank" rel="noopener noreferrer" className={styles.website}>
                    <ExternalLink size={14} />
                    Website
                  </a>
                )}
              </div>
            </div>
          )}
        </section>

        {/* Deals (P-05) */}
        {vendorDeals.length > 0 && (
          <section className={styles.dealsSection}>
            <h3 className={styles.sectionTitle}>
              <Tag size={18} />
              Active Deals
            </h3>
            <div className={styles.dealsList}>
              {vendorDeals.map((deal) => (
                <div key={deal.id} className={styles.dealItem}>
                  <div className={styles.dealBadge}>
                    {deal.discount_type === 'PERCENTAGE'
                      ? `${deal.discount_value}% OFF`
                      : deal.discount_type === 'BOGO'
                        ? 'BOGO'
                        : `PKR ${deal.discount_value} OFF`}
                  </div>
                  <div className={styles.dealInfo}>
                    <strong>{deal.title}</strong>
                    <p>{deal.description}</p>
                    <CountdownTimer endDate={deal.end_date} size="sm" />
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Tags */}
        {vendor.tags && vendor.tags.length > 0 && (
          <section className={styles.tagsSection}>
            <h3 className={styles.sectionTitle}>
              <Tag size={18} />
              Tags
            </h3>
            <div className={styles.tagList}>
              {vendor.tags.map((tag) => (
                <TagChip key={tag} label={tag} />
              ))}
            </div>
          </section>
        )}

        {/* Reels */}
        {reels.length > 0 && (
          <section className={styles.reelsSection}>
            <h3 className={styles.sectionTitle}>
              <Film size={18} />
              Reels ({vendor.reel_count})
            </h3>
            <div className={styles.reelsGrid}>
              {reels.slice(0, 6).map((reel) => (
                <Link key={reel.id} to="/reels" className={styles.reelThumbnail}>
                  {reel.thumbnail_url ? (
                    <img src={reel.thumbnail_url} alt={reel.title} loading="lazy" />
                  ) : (
                    <div className={styles.reelPlaceholder}><Film size={20} /></div>
                  )}
                  <div className={styles.reelOverlay}>
                    <Camera size={16} />
                  </div>
                </Link>
              ))}
            </div>
          </section>
        )}

        {/* Similar Vendors */}
        {similar.length > 0 && (
          <section className={styles.similarSection}>
            <h3 className={styles.sectionTitle}>
              <MapPin size={18} />
              More Nearby
            </h3>
            <div className={styles.similarList}>
              {similar.slice(0, 4).map((v) => (
                <VendorCard key={v.id} vendor={v} />
              ))}
            </div>
          </section>
        )}
      </main>
    </div>
  );
}
