import { useEffect, useMemo, useRef, useState, useCallback } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Camera, Map, List, Mic, Search, Tag, User, Settings, RefreshCw, Maximize2, RotateCcw, X, Volume2, ChevronRight } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { useDiscoveryStore } from '@/store/discoveryStore';
import { useAuthStore } from '@/store/authStore';
import { useUIStore } from '@/store/uiStore';
import { useLocation } from '@/hooks/useLocation';
import { useVoice } from '@/hooks/useVoice';
import { VendorCard } from '@/components/dls/VendorCard';
import { VendorListSkeleton } from '@/components/dls/SkeletonLoader';
import { OfflineBanner } from '@/components/dls/OfflineBanner';
import { getNearbyVendors, getMapPins, getARMarkers, voiceSearch, getTagBrowser, getSearchSuggestions, getPromotionsStrip } from '@/api/discovery';
import { queryKeys } from '@/queryKeys';
import { TIER_COLORS, MAP_DEFAULTS, DISCOVERY_DEFAULTS } from '@/utils/constants';
import mapboxgl from 'mapbox-gl';
import 'mapbox-gl/dist/mapbox-gl.css';
import styles from './DiscoveryPage.module.css';

export default function DiscoveryPage() {
  const navigate = useNavigate();
  const activeView = useDiscoveryStore((s) => s.activeView);
  const setActiveView = useDiscoveryStore((s) => s.setActiveView);
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const theme = useUIStore((s) => s.theme);
  const { location, locationError, requestLocation } = useLocation();
  
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<mapboxgl.Map | null>(null);
  const [mapReady, setMapReady] = useState(false);
  
  // AR Camera state
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [cameraActive, setCameraActive] = useState(false);
  const [cameraError, setCameraError] = useState<string | null>(null);
  const [arReady, setArReady] = useState(false);
  
  // Voice search state
  const [voiceModalOpen, setVoiceModalOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const {
    state: voiceState,
    transcript,
    interimTranscript,
    isSupported,
    start,
    stop,
    reset,
  } = useVoice();

  // Search bar state
  const [searchInput, setSearchInput] = useState('');
  const [showSuggestions, setShowSuggestions] = useState(false);
  const searchTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [debouncedSearch, setDebouncedSearch] = useState('');

  // Tag browser state
  const [tagModalOpen, setTagModalOpen] = useState(false);
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [appliedTags, setAppliedTags] = useState<string[]>([]);

  useEffect(() => {
    requestLocation();
  }, [requestLocation]);

  // Initialize Mapbox token
  useEffect(() => {
    if (import.meta.env.VITE_MAPBOX_TOKEN) {
      mapboxgl.accessToken = import.meta.env.VITE_MAPBOX_TOKEN;
    }
  }, []);

  // Initialize map when location is available and map view is active
  useEffect(() => {
    if (!location || !mapContainer.current || activeView !== 'map' || map.current) {
      return;
    }

    const mapStyle = theme === 'dark' ? MAP_DEFAULTS.style : MAP_DEFAULTS.styleLight;
    const mapInstance = new mapboxgl.Map({
      container: mapContainer.current,
      style: mapStyle,
      center: [location.lng, location.lat],
      zoom: MAP_DEFAULTS.zoom,
      pitch: 45,
      bearing: -17.6,
      antialias: true,
    });

    map.current = mapInstance;

    mapInstance.on('load', () => {
      setMapReady(true);
    });

    return () => {
      if (map.current) {
        map.current.remove();
        map.current = null;
        setMapReady(false);
      }
    };
  }, [location, activeView]);

  // Debounced search input handler
  const handleSearchChange = useCallback((value: string) => {
    setSearchInput(value);
    if (searchTimeout.current) clearTimeout(searchTimeout.current);
    if (value.length > 1) {
      searchTimeout.current = setTimeout(() => {
        setDebouncedSearch(value);
        setShowSuggestions(true);
      }, 300);
    } else {
      setDebouncedSearch('');
      setShowSuggestions(false);
    }
  }, []);

  const handleSearchSubmit = useCallback((q: string) => {
    setSearchInput(q);
    setDebouncedSearch('');
    setShowSuggestions(false);
    setSearchQuery(q);
  }, []);

  // Search suggestions query (M-26)
  const { data: suggestions } = useQuery({
    queryKey: queryKeys.discovery.suggestions(debouncedSearch),
    queryFn: () => getSearchSuggestions(debouncedSearch),
    enabled: debouncedSearch.length > 1,
    staleTime: 60_000,
  });

  // Promotions strip query (M-02)
  const { data: promotionsStrip } = useQuery({
    queryKey: queryKeys.discovery.promotionsStrip(location?.lat ?? 0, location?.lng ?? 0),
    queryFn: () => getPromotionsStrip(location!.lat, location!.lng),
    enabled: !!location,
    staleTime: 5 * 60 * 1000,
  });

  const {
    data: vendors,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: queryKeys.discovery.nearby(location?.lat ?? 0, location?.lng ?? 0, DISCOVERY_DEFAULTS.radiusKm, appliedTags, searchInput),
    queryFn: () => getNearbyVendors({
      lat: location!.lat,
      lng: location!.lng,
      radius_km: DISCOVERY_DEFAULTS.radiusKm,
      tags: appliedTags,
      q: searchInput || undefined,
    }),
    enabled: !!location,
    staleTime: 5 * 60 * 1000,
  });

  const vendorList = useMemo(() => vendors?.data?.results || [], [vendors]);

  // Query for map pins
  const {
    data: mapPins,
    error: pinsError,
  } = useQuery({
    queryKey: queryKeys.discovery.mapPins(location?.lat ?? 0, location?.lng ?? 0, 2),
    queryFn: () => getMapPins(location!.lat, location!.lng, 2),
    enabled: !!location && activeView === 'map',
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  // Camera management for AR view
  const startCamera = useCallback(async () => {
    try {
      setCameraError(null);
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: 'environment',
          width: { ideal: 1920 },
          height: { ideal: 1080 }
        },
        audio: false
      });
      
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        streamRef.current = stream;
        setCameraActive(true);
        setArReady(true);
      }
    } catch (error) {
      setCameraError('Unable to access camera. Please check permissions.');
      setCameraActive(false);
      setArReady(false);
    }
  }, []);

  const stopCamera = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    setCameraActive(false);
    setArReady(false);
  }, []);

  // Initialize camera when AR view is active
  useEffect(() => {
    if (activeView === 'ar' && location && !cameraActive) {
      startCamera();
    } else if (activeView !== 'ar' && cameraActive) {
      stopCamera();
    }

    return () => {
      if (activeView !== 'ar') {
        stopCamera();
      }
    };
  }, [activeView, location, cameraActive, startCamera, stopCamera]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopCamera();
    };
  }, [stopCamera]);

  // Voice search handlers
  const handleVoiceSearchOpen = useCallback(() => {
    setVoiceModalOpen(true);
    reset();
  }, [reset]);

  const handleVoiceSearchClose = useCallback(() => {
    setVoiceModalOpen(false);
    if (voiceState === 'listening') {
      stop();
    }
    reset();
  }, [voiceState, stop, reset]);

  const handleVoiceToggle = useCallback(() => {
    if (voiceState === 'listening') {
      stop();
    } else {
      start();
    }
  }, [voiceState, start, stop]);

  // Update search query when transcript changes
  useEffect(() => {
    if (transcript.trim()) {
      setSearchQuery(transcript);
    }
  }, [transcript]);

  // Voice search query
  const {
    data: voiceResults,
    isLoading: voiceLoading,
    error: voiceError,
  } = useQuery({
    queryKey: queryKeys.discovery.search(searchQuery),
    queryFn: () => voiceSearch(searchQuery),
    enabled: !!searchQuery && searchQuery.length > 2,
    staleTime: 2 * 60 * 1000, // 2 minutes
  });

  // Tag browser query
  const {
    data: tagData,
    isLoading: tagsLoading,
    error: tagsError,
  } = useQuery({
    queryKey: queryKeys.tags.browser(location?.lat ?? 0, location?.lng ?? 0),
    queryFn: () => getTagBrowser(location!.lat, location!.lng),
    enabled: !!location,
    staleTime: 10 * 60 * 1000, // 10 minutes
  });

  // Tag browser handlers
  const handleTagBrowserOpen = useCallback(() => {
    setTagModalOpen(true);
  }, []);

  const handleTagBrowserClose = useCallback(() => {
    setTagModalOpen(false);
  }, []);

  const handleTagToggle = useCallback((tag: string) => {
    setSelectedTags(prev => 
      prev.includes(tag) 
        ? prev.filter(t => t !== tag)
        : [...prev, tag]
    );
  }, []);

  const handleTagsApply = useCallback(() => {
    setAppliedTags([...selectedTags]);
    setTagModalOpen(false);
  }, [selectedTags]);

  // Add vendor pins to map when data is available
  useEffect(() => {
    if (!map.current || !mapReady || !mapPins?.data) {
      return;
    }

    const mapInstance = map.current;
    const pins = mapPins.data;

    // Remove existing markers
    const existingMarkers = document.querySelectorAll('.mapboxgl-marker');
    existingMarkers.forEach(marker => marker.remove());

    // Add new markers for each vendor (W-03: Custom tier-colored pins)
    pins.forEach((pin) => {
      const tierColor = TIER_COLORS[pin.subscription_tier] || 'var(--color-grey-400)';
      const el = document.createElement('div');
      el.className = styles.mapMarker;
      const initial = pin.business_name.charAt(0).toUpperCase();
      const promoClass = pin.has_active_promotion ? styles.markerPulse : '';
      el.innerHTML = `
        <div class="${styles.markerPin} ${promoClass}" style="--marker-tier-color: ${tierColor}">
          <div class="${styles.markerCircle}">${pin.logo_url ? `<img src="${pin.logo_url}" alt="" class="${styles.markerLogo}"/>` : `<span>${initial}</span>`}</div>
          <div class="${styles.markerArrow}"></div>
        </div>
      `;

      const marker = new mapboxgl.Marker({
        element: el,
        anchor: 'bottom',
      })
        .setLngLat([pin.location.coordinates[0], pin.location.coordinates[1]])
        .addTo(mapInstance);

      const popup = new mapboxgl.Popup({
        offset: 25,
        closeButton: false,
      }).setHTML(`
        <div class="${styles.mapPopup}">
          <strong>${pin.business_name}</strong><br>
          <small>${pin.category}</small>
        </div>
      `);

      marker.setPopup(popup);

      el.addEventListener('click', () => {
        navigate(`/vendor/${pin.vendor_id}`);
      });
    });
  }, [mapPins, mapReady]);

  // Query for AR markers
  const {
    data: arMarkers,
  } = useQuery({
    queryKey: queryKeys.discovery.arMarkers(location?.lat ?? 0, location?.lng ?? 0, 1),
    queryFn: () => getARMarkers(location!.lat, location!.lng, 1),
    enabled: !!location && activeView === 'ar',
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  return (
    <div className={styles.page}>
      <header className={styles.topBar}>
        <div className={styles.topBarLeft}>
          <Link to="/" className={styles.logoLink}>
            <img src="/airad_icon.png" alt="AirAd" className={styles.logo} />
          </Link>
        </div>
        <div className={styles.searchWrap}>
          <Search size={18} className={styles.searchIcon} />
          <input
            type="text"
            placeholder="Search vendors, tags, or say something…"
            className={styles.searchInput}
            value={searchInput}
            onChange={(e) => handleSearchChange(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter' && searchInput.trim()) handleSearchSubmit(searchInput.trim()); }}
            onFocus={() => { if (debouncedSearch.length > 1) setShowSuggestions(true); }}
            onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
            aria-autocomplete="list"
            aria-expanded={showSuggestions && !!suggestions?.data?.length}
          />
          <button 
            className={styles.micBtn} 
            aria-label="Voice search"
            onClick={handleVoiceSearchOpen}
          >
            <Mic size={18} />
          </button>
          {showSuggestions && suggestions?.data && suggestions.data.length > 0 && (
            <div className={styles.suggestionsDropdown} role="listbox">
              {suggestions.data.map((s) => (
                <button
                  key={`${s.type}-${s.slug}`}
                  className={styles.suggestionItem}
                  role="option"
                  onMouseDown={() => {
                    if (s.vendor_id) navigate(`/vendor/${s.vendor_id}`);
                    else handleSearchSubmit(s.label);
                  }}
                >
                  <span className={styles.suggestionType}>{s.type}</span>
                  <span className={styles.suggestionLabel}>{s.label}</span>
                  <ChevronRight size={14} className={styles.suggestionArrow} />
                </button>
              ))}
            </div>
          )}
        </div>
        <div className={styles.topBarRight}>
          <button 
            className={styles.iconBtn} 
            aria-label="Tags"
            onClick={handleTagBrowserOpen}
          >
            <Tag size={20} />
          </button>
          <Link to="/preferences" className={styles.iconBtn} aria-label="Settings">
            <Settings size={20} />
          </Link>
          {!isAuthenticated && (
            <Link to="/login" className={styles.iconBtn} aria-label="Sign in">
              <User size={20} />
            </Link>
          )}
        </div>
      </header>

      {/* Applied tags indicator */}
      {appliedTags.length > 0 && (
        <div className={styles.appliedTagsBar}>
          <span className={styles.appliedLabel}>Filtered by:</span>
          {appliedTags.map((tag) => (
            <span key={tag} className={styles.appliedTag}>
              {tag}
              <button
                className={styles.removeTagBtn}
                onClick={() => {
                  const next = appliedTags.filter((t) => t !== tag);
                  setAppliedTags(next);
                  setSelectedTags(next);
                }}
                aria-label={`Remove ${tag} filter`}
              >
                <X size={12} />
              </button>
            </span>
          ))}
          <button className={styles.clearTagsBtn} onClick={() => { setAppliedTags([]); setSelectedTags([]); }}>
            Clear all
          </button>
        </div>
      )}

      {/* Promotions Strip (M-02) */}
      {promotionsStrip?.data && promotionsStrip.data.length > 0 && (
        <div className={styles.promosStrip} aria-label="Active promotions">
          {promotionsStrip.data.map((promo) => (
            <button
              key={promo.id}
              className={styles.promoChip}
              onClick={() => navigate(`/vendor/${promo.vendor_id}`)}
            >
              <span className={styles.promoVendor}>{promo.vendor_name}</span>
              <span className={styles.promoHeadline}>{promo.headline}</span>
            </button>
          ))}
        </div>
      )}

      <main className={styles.content} id="main-content">
        {locationError && (
          <div className={styles.locationError} role="alert">
            <p>{locationError}</p>
            <button onClick={requestLocation} className={styles.retryBtn}>
              Allow Location
            </button>
          </div>
        )}

        {!locationError && !location && (
          <div className={styles.locationLoading}>
            <div className={styles.spinner} />
            <p>Getting your location…</p>
          </div>
        )}

        {location && (
          <div className={styles.viewContainer}>
            {activeView === 'ar' && (
              <div className={styles.arView}>
                <video
                  ref={videoRef}
                  autoPlay
                  playsInline
                  muted
                  className={styles.arVideo}
                />
                <canvas
                  ref={canvasRef}
                  className={styles.arCanvas}
                />
                
                {/* AR Overlay */}
                <div className={styles.arOverlay}>
                  {cameraError && (
                    <div className={styles.cameraError} role="alert">
                      <Camera size={24} />
                      <p>{cameraError}</p>
                      <button onClick={startCamera} className={styles.retryBtn}>
                        <RotateCcw size={16} />
                        Retry Camera
                      </button>
                    </div>
                  )}
                  
                  {!cameraError && !arReady && (
                    <div className={styles.cameraLoading}>
                      <div className={styles.spinner} />
                      <p>Starting camera…</p>
                    </div>
                  )}
                  
                  {arReady && arMarkers?.data && (
                    <div className={styles.arBubbles}>
                      {arMarkers.data.map((marker) => (
                        <div
                          key={marker.vendor_id}
                          className={styles.arBubble}
                          onClick={() => {
                            navigate(`/vendor/${marker.vendor_id}`);
                          }}
                        >
                          <div className={styles.bubbleContent}>
                            <div className={styles.bubbleTier} style={{ '--tier-color': TIER_COLORS[marker.subscription_tier] || 'var(--color-grey-400)' } as React.CSSProperties} />
                            <div className={styles.bubbleInfo}>
                              <strong>{marker.business_name}</strong>
                              <small>{(marker.distance_m / 1000).toFixed(1)}km</small>
                            </div>
                          </div>
                          <div className={styles.bubbleArrow} />
                        </div>
                      ))}
                    </div>
                  )}
                  
                  {/* AR Controls */}
                  <div className={styles.arControls}>
                    <button className={styles.arControlBtn} aria-label="Fullscreen">
                      <Maximize2 size={20} />
                    </button>
                  </div>
                </div>
              </div>
            )}
            {activeView === 'map' && (
              <div className={styles.mapView}>
                <div 
                  ref={mapContainer} 
                  className={styles.mapContainer}
                  role="application"
                  aria-label="Interactive map showing nearby vendors"
                />
                {!mapReady && (
                  <div className={styles.mapLoading}>
                    <div className={styles.spinner} />
                    <p>Loading map…</p>
                  </div>
                )}
                {pinsError && (
                  <div className={styles.mapError} role="alert">
                    <p>Failed to load map data</p>
                  </div>
                )}
              </div>
            )}
            {activeView === 'list' && (
              <div className={styles.listView}>
                {isLoading && (
                  <div className={styles.loadingState}>
                    <VendorListSkeleton count={5} />
                  </div>
                )}
                
                {error && (
                  <div className={styles.errorState} role="alert">
                    <p>Failed to load nearby vendors</p>
                    <button onClick={() => refetch()} className={styles.retryBtn}>
                      <RefreshCw size={16} />
                      Retry
                    </button>
                  </div>
                )}

                {!isLoading && !error && vendorList.length === 0 && (
                  <div className={styles.emptyState}>
                    <List size={48} />
                    <h2>No vendors nearby</h2>
                    <p>Try moving to a different location or expanding your search area</p>
                  </div>
                )}

                {!isLoading && !error && vendorList.length > 0 && (
                  <div className={styles.vendorList}>
                    {vendorList.map((vendor) => (
                      <VendorCard
                        key={vendor.id}
                        vendor={vendor}
                      />
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </main>

      <nav className={styles.bottomNav} aria-label="Discovery views">
        <button
          className={`${styles.navItem} ${activeView === 'ar' ? styles.navItemActive : ''}`}
          onClick={() => setActiveView('ar')}
        >
          <Camera size={22} />
          <span>AR</span>
        </button>
        <button
          className={`${styles.navItem} ${activeView === 'map' ? styles.navItemActive : ''}`}
          onClick={() => setActiveView('map')}
        >
          <Map size={22} />
          <span>Map</span>
        </button>
        <button
          className={`${styles.navItem} ${activeView === 'list' ? styles.navItemActive : ''}`}
          onClick={() => setActiveView('list')}
        >
          <List size={22} />
          <span>List</span>
        </button>
      </nav>

      <OfflineBanner />

      {/* Voice Search Modal */}
      {voiceModalOpen && (
        <div className={styles.voiceModalOverlay} onClick={handleVoiceSearchClose}>
          <div 
            className={styles.voiceModal}
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-modal="true"
            aria-labelledby="voice-search-title"
          >
            <div className={styles.voiceModalHeader}>
              <h2 id="voice-search-title" className={styles.voiceModalTitle}>
                Voice Search
              </h2>
              <button 
                className={styles.closeBtn}
                onClick={handleVoiceSearchClose}
                aria-label="Close voice search"
              >
                <X size={20} />
              </button>
            </div>

            <div className={styles.voiceModalContent}>
              {!isSupported && (
                <div className={styles.voiceError}>
                  <Volume2 size={24} />
                  <p>Voice search is not supported in your browser</p>
                </div>
              )}

              {isSupported && (
                <>
                  <div className={styles.voiceVisualizer}>
                    <button
                      className={`${styles.voiceBtn} ${voiceState === 'listening' ? styles.listening : ''}`}
                      onClick={handleVoiceToggle}
                      aria-label={voiceState === 'listening' ? 'Stop listening' : 'Start listening'}
                    >
                      <Mic size={32} />
                      {voiceState === 'listening' && (
                        <div className={styles.voiceWave}>
                          <span></span>
                          <span></span>
                          <span></span>
                          <span></span>
                          <span></span>
                        </div>
                      )}
                    </button>
                  </div>

                  <div className={styles.voiceTranscript}>
                    {transcript ? (
                      <p className={styles.transcriptText}>"{transcript}"</p>
                    ) : interimTranscript ? (
                      <p className={styles.transcriptInterim}>"{interimTranscript}"</p>
                    ) : (
                      <p className={styles.transcriptPlaceholder}>
                        {voiceState === 'listening' ? 'Listening…' : 'Tap the microphone to start'}
                      </p>
                    )}
                  </div>

                  {searchQuery && (
                    <div className={styles.voiceResults}>
                      {voiceLoading && (
                        <div className={styles.resultsLoading}>
                          <div className={styles.spinner} />
                          <p>Searching...</p>
                        </div>
                      )}

                      {voiceError && (
                        <div className={styles.resultsError}>
                          <p>Search failed. Please try again.</p>
                        </div>
                      )}

                      {voiceResults?.data && (
                        <div className={styles.resultsList}>
                          <h3>Results for "{searchQuery}"</h3>
                          {voiceResults.data.vendors.slice(0, 5).map((result) => (
                            <div
                              key={result.id}
                              className={styles.resultItem}
                              onClick={() => {
                                navigate(`/vendor/${result.id}`);
                              }}
                            >
                              <div className={styles.resultInfo}>
                                <strong>{result.business_name}</strong>
                                <small>{result.category} • {result.distance_km.toFixed(1)}km</small>
                              </div>
                              <div 
                                className={styles.resultTier}
                                style={{ '--tier-color': TIER_COLORS[result.subscription_tier] || 'var(--color-grey-400)' } as React.CSSProperties}
                              />
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Tag Browser Modal */}
      {tagModalOpen && (
        <div className={styles.tagModalOverlay} onClick={handleTagBrowserClose}>
          <div 
            className={styles.tagModal}
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-modal="true"
            aria-labelledby="tag-browser-title"
          >
            <div className={styles.tagModalHeader}>
              <h2 id="tag-browser-title" className={styles.tagModalTitle}>
                Browse Tags
              </h2>
              <button 
                className={styles.closeBtn}
                onClick={handleTagBrowserClose}
                aria-label="Close tag browser"
              >
                <X size={20} />
              </button>
            </div>

            <div className={styles.tagModalContent}>
              {tagsLoading && (
                <div className={styles.tagsLoading}>
                  <div className={styles.spinner} />
                  <p>Loading tags…</p>
                </div>
              )}

              {tagsError && (
                <div className={styles.tagsError}>
                  <p>Failed to load tags. Please try again.</p>
                </div>
              )}

              {tagData?.data && (
                <>
                  <div className={styles.tagCategories}>
                    {tagData.data.map((group) => (
                      <div key={group.section} className={styles.tagCategory}>
                        <h3 className={styles.categoryName}>{group.label}</h3>
                        <div className={styles.tagList}>
                          {group.tags.map((tag) => (
                            <button
                              key={tag.slug}
                              className={`${styles.tagChip} ${
                                selectedTags.includes(tag.slug) ? styles.selected : ''
                              }`}
                              onClick={() => handleTagToggle(tag.slug)}
                            >
                              {tag.label}
                              <span className={styles.tagCount}>({tag.count})</span>
                            </button>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>

                  {selectedTags.length > 0 && (
                    <div className={styles.tagActions}>
                      <div className={styles.selectedTags}>
                        <span>Selected: {selectedTags.join(', ')}</span>
                      </div>
                      <button 
                        className={styles.applyBtn}
                        onClick={handleTagsApply}
                      >
                        Apply Tags ({selectedTags.length})
                      </button>
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
