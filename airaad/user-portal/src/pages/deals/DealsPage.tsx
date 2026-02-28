import { useState, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { 
  ArrowLeft, 
  Percent, 
  Filter, 
  Clock, 
  Search,
  ChevronDown,
  Zap
} from 'lucide-react';
import { getNearbyDeals } from '@/api/deals';
import { queryKeys } from '@/queryKeys';
import { CountdownTimer } from '@/components/dls/CountdownTimer';
import { useLocation } from '@/hooks/useLocation';
import styles from './DealsPage.module.css';

function getUrgencyClass(endDate: string): string {
  const hoursLeft = (new Date(endDate).getTime() - Date.now()) / (1000 * 60 * 60);
  if (hoursLeft <= 0) return styles.urgencyExpired;
  if (hoursLeft <= 2) return styles.urgencyCritical;
  if (hoursLeft <= 6) return styles.urgencyHigh;
  if (hoursLeft <= 24) return styles.urgencyMedium;
  return '';
}

export default function DealsPage() {
  const { location } = useLocation();
  const [searchQuery, setSearchQuery] = useState('');
  const [sortBy, setSortBy] = useState<'ending_soon' | 'highest_discount' | 'newest'>('ending_soon');
  const [showFilters, setShowFilters] = useState(false);

  const {
    data: dealsRes,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: queryKeys.deals.nearby(location?.lat ?? 0, location?.lng ?? 0),
    queryFn: () => getNearbyDeals(location!.lat, location!.lng),
    enabled: !!location,
    staleTime: 2 * 60 * 1000,
  });

  const deals = dealsRes?.data ?? [];

  const filteredDeals = useMemo(() => {
    let filtered = [...deals];

    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      filtered = filtered.filter(deal =>
        deal.title.toLowerCase().includes(q) ||
        deal.description.toLowerCase().includes(q) ||
        deal.vendor_name.toLowerCase().includes(q)
      );
    }

    filtered.sort((a, b) => {
      switch (sortBy) {
        case 'ending_soon':
          return new Date(a.end_date).getTime() - new Date(b.end_date).getTime();
        case 'highest_discount':
          return b.discount_value - a.discount_value;
        case 'newest':
          return new Date(b.start_date).getTime() - new Date(a.start_date).getTime();
        default:
          return 0;
      }
    });

    return filtered;
  }, [deals, searchQuery, sortBy]);

  if (isLoading) {
    return (
      <div className={styles.page}>
        <header className={styles.topBar}>
          <Link to="/discover" className={styles.backBtn} aria-label="Back">
            <ArrowLeft size={20} />
          </Link>
          <h1 className={styles.title}>Loading Deals…</h1>
        </header>
        <main className={styles.content} id="main-content">
          <div className={styles.skeletonGrid}>
            {[...Array(6)].map((_, i) => (
              <div key={i} className={styles.dealSkeleton} />
            ))}
          </div>
        </main>
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.page}>
        <header className={styles.topBar}>
          <Link to="/discover" className={styles.backBtn} aria-label="Back">
            <ArrowLeft size={20} />
          </Link>
          <h1 className={styles.title}>Deals & Offers</h1>
        </header>
        <main className={styles.content} id="main-content">
          <div className={styles.errorState}>
            <Percent size={48} />
            <h2>Unable to load deals</h2>
            <p>Please check your connection and try again.</p>
            <button onClick={() => refetch()} className={styles.retryBtn}>
              Retry
            </button>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <header className={styles.topBar}>
        <Link to="/discover" className={styles.backBtn} aria-label="Back">
          <ArrowLeft size={20} />
        </Link>
        <h1 className={styles.title}>Deals & Offers</h1>
      </header>

      <main className={styles.content} id="main-content">
        {/* Search and Filters */}
        <section className={styles.searchSection}>
          <div className={styles.searchBar}>
            <Search size={18} className={styles.searchIcon} />
            <input
              type="text"
              placeholder="Search deals, vendors…"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className={styles.searchInput}
            />
          </div>
          
          <button 
            className={styles.filterBtn}
            onClick={() => setShowFilters(!showFilters)}
            aria-expanded={showFilters}
          >
            <Filter size={18} />
            Sort
            <ChevronDown size={16} className={`${styles.chevron} ${showFilters ? styles.open : ''}`} />
          </button>
        </section>

        {showFilters && (
          <section className={styles.filterPanel}>
            <div className={styles.filterGroup}>
              <label className={styles.filterLabel}>Sort By</label>
              <select 
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as typeof sortBy)}
                className={styles.filterSelect}
              >
                <option value="ending_soon">Ending Soon</option>
                <option value="highest_discount">Highest Discount</option>
                <option value="newest">Newest</option>
              </select>
            </div>
          </section>
        )}

        {/* Results Summary */}
        <section className={styles.resultsSummary}>
          <p>{filteredDeals.length} deal{filteredDeals.length !== 1 ? 's' : ''} found</p>
        </section>

        {/* Deals Grid */}
        <section className={styles.dealsGrid}>
          {filteredDeals.length === 0 ? (
            <div className={styles.emptyState}>
              <Percent size={48} />
              <h3>No deals found</h3>
              <p>Try adjusting your search terms</p>
            </div>
          ) : (
            filteredDeals.map((deal) => (
              <Link 
                key={deal.id} 
                to={`/vendor/${deal.vendor_id}`}
                className={`${styles.dealCard} ${getUrgencyClass(deal.end_date)}`}
              >
                <div className={styles.dealImage}>
                  {deal.image_url ? (
                    <img src={deal.image_url} alt={deal.title} />
                  ) : (
                    <div className={styles.imagePlaceholder}>
                      <Percent size={32} />
                    </div>
                  )}
                  <div className={styles.discountBadge}>
                    {deal.is_flash_deal && <Zap size={12} />}
                    {deal.discount_type === 'PERCENTAGE'
                      ? `${deal.discount_value}% OFF`
                      : deal.discount_type === 'BOGO'
                        ? 'Buy 1 Get 1'
                        : `PKR ${deal.discount_value} OFF`}
                  </div>
                </div>
                
                <div className={styles.dealContent}>
                  <h3 className={styles.dealTitle}>{deal.title}</h3>
                  <p className={styles.dealDescription}>{deal.description}</p>
                  
                  <div className={styles.vendorInfo}>
                    <h4 className={styles.vendorName}>{deal.vendor_name}</h4>
                  </div>
                  
                  <div className={styles.dealFooter}>
                    <div className={styles.expiryInfo}>
                      <Clock size={14} />
                      <CountdownTimer endDate={deal.end_date} size="sm" />
                    </div>
                  </div>
                </div>
              </Link>
            ))
          )}
        </section>
      </main>
    </div>
  );
}
