import { useState, useCallback } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { MapPin, Search, Navigation } from 'lucide-react';
import { searchVendors, getNearbyVendors } from '@/api/vendor';
import { queryKeys } from '@/queryKeys';
import type { NearbyVendor } from '@/api/vendor';
import styles from './ClaimSearchPage.module.css';

export default function ClaimSearchPage() {
  const navigate = useNavigate();
  const [query, setQuery] = useState('');
  const [gpsCoords, setGpsCoords] = useState<{ lat: number; lng: number } | null>(null);
  const [gpsLoading, setGpsLoading] = useState(false);
  const [gpsError, setGpsError] = useState('');

  const searchQuery = useQuery({
    queryKey: queryKeys.vendor.search(query),
    queryFn: () => searchVendors(query),
    enabled: query.length >= 2,
    staleTime: 30_000,
  });

  const nearbyQuery = useQuery({
    queryKey: queryKeys.vendor.nearby(gpsCoords?.lat ?? 0, gpsCoords?.lng ?? 0),
    queryFn: () => getNearbyVendors(gpsCoords!.lat, gpsCoords!.lng),
    enabled: gpsCoords !== null,
    staleTime: 60_000,
  });

  const handleUseGps = useCallback(() => {
    if (!navigator.geolocation) {
      setGpsError('Geolocation is not supported by your browser.');
      return;
    }
    setGpsLoading(true);
    setGpsError('');
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setGpsCoords({ lat: pos.coords.latitude, lng: pos.coords.longitude });
        setGpsLoading(false);
      },
      () => {
        setGpsError('Could not detect your location. Please search manually.');
        setGpsLoading(false);
      },
      { enableHighAccuracy: true, timeout: 10000 },
    );
  }, []);

  const handleClaim = useCallback(
    (vendor: NearbyVendor) => {
      navigate(`/onboarding/verify/${vendor.id}`, { state: { vendor } });
    },
    [navigate],
  );

  const vendors: NearbyVendor[] = query.length >= 2
    ? (searchQuery.data ?? [])
    : (nearbyQuery.data ?? []);

  const isLoading = query.length >= 2 ? searchQuery.isLoading : nearbyQuery.isLoading;

  return (
    <div className={styles.page}>
      <div className={styles.inner}>
        <Link to="/" className="onboarding-logo">
          <img src="/airad_icon.png" alt="AirAd" className="onboarding-logo-icon" />
          <span className="onboarding-logo-text">AirAd</span>
        </Link>
        <h1 className={styles.heading}>Find Your Business</h1>
        <p className={styles.subtext}>
          Search by name or use your location to find nearby businesses on AirAd.
        </p>

        <div className={styles.searchRow}>
          <input
            type="text"
            className={styles.searchInput}
            placeholder="Search by business name or area..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            autoFocus
          />
          <button
            className={styles.gpsBtn}
            onClick={handleUseGps}
            disabled={gpsLoading}
            type="button"
          >
            <Navigation size={16} strokeWidth={1.5} />
            {gpsLoading ? 'Detecting...' : 'Use GPS'}
          </button>
        </div>

        {gpsError && (
          <p className="gps-error">
            {gpsError}
          </p>
        )}

        {gpsCoords && !query && (
          <div className={styles.divider}>Businesses near you</div>
        )}

        {isLoading && (
          <div className={styles.loading}>Searching...</div>
        )}

        {!isLoading && vendors.length === 0 && (query.length >= 2 || gpsCoords) && (
          <div className={styles.emptyState}>
            <Search size={32} strokeWidth={1.5} className="empty-icon" />
            No businesses found. Try a different search term or check your location.
          </div>
        )}

        {vendors.length > 0 && (
          <div className={styles.results}>
            {vendors.map((v) => (
              <div key={v.id} className={styles.vendorCard}>
                <div className={styles.vendorInfo}>
                  <span className={styles.vendorName}>{v.business_name}</span>
                  <span className={styles.vendorAddress}>{v.address_text}{v.area_name ? `, ${v.area_name}` : ''}</span>
                  {v.distance_meters !== null && (
                    <span className={styles.vendorDistance}>
                      <MapPin size={12} strokeWidth={1.5} className="inline-icon" />
                      {v.distance_meters < 1000
                        ? `${Math.round(v.distance_meters)}m away`
                        : `${(v.distance_meters / 1000).toFixed(1)}km away`}
                    </span>
                  )}
                </div>
                {v.claimed_status === 'UNCLAIMED' ? (
                  <button
                    className={styles.claimBtn}
                    onClick={() => handleClaim(v)}
                    type="button"
                  >
                    Claim This Business
                  </button>
                ) : (
                  <span className="claimed-label">
                    {v.claimed_status === 'CLAIM_PENDING' ? 'Claim pending' : 'Already claimed'}
                  </span>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
