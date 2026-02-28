import { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { 
  ArrowLeft, 
  Navigation2, 
  Clock, 
  Footprints,
  RotateCcw,
  Volume2,
  VolumeX,
  Maximize2,
  Minimize2,
  AlertCircle
} from 'lucide-react';
import { getVendorDetail } from '@/api/vendor';
import { recordArrival } from '@/api/navigation';
import { queryKeys } from '@/queryKeys';
import { formatDistance } from '@/utils/formatters';
import { useLocation } from '@/hooks/useLocation';
import mapboxgl from 'mapbox-gl';
import 'mapbox-gl/dist/mapbox-gl.css';
import styles from './NavigationPage.module.css';

interface MapboxManeuver {
  instruction: string;
  type: string;
}

interface MapboxStep {
  maneuver: MapboxManeuver;
  distance: number;
  duration: number;
}

interface DirectionsStep {
  instruction: string;
  distance: number;
  duration: number;
  maneuver: string;
}

interface DirectionsData {
  distance: number;
  duration: number;
  geometry: GeoJSON.LineString;
  steps: DirectionsStep[];
}

async function fetchWalkingDirections(
  fromLng: number,
  fromLat: number,
  toLng: number,
  toLat: number,
): Promise<DirectionsData | null> {
  const token = import.meta.env.VITE_MAPBOX_TOKEN;
  if (!token) return null;
  const url = `https://api.mapbox.com/directions/v5/mapbox/walking/${fromLng},${fromLat};${toLng},${toLat}?geometries=geojson&steps=true&access_token=${token}`;
  const res = await fetch(url);
  if (!res.ok) return null;
  const json = await res.json();
  const route = json.routes?.[0];
  if (!route) return null;
  return {
    distance: route.distance,
    duration: route.duration,
    geometry: route.geometry,
    steps: route.legs[0].steps.map((s: MapboxStep) => ({
      instruction: s.maneuver.instruction,
      distance: s.distance,
      duration: s.duration,
      maneuver: s.maneuver.type,
    })),
  };
}

export default function NavigationPage() {
  const { vendorId } = useParams<{ vendorId: string }>();
  const { location: currentLocation } = useLocation();
  const mapContainer = useRef<HTMLDivElement>(null);
  const mapRef = useRef<mapboxgl.Map | null>(null);
  const [isNavigating, setIsNavigating] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [isMuted, setIsMuted] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [directions, setDirections] = useState<DirectionsData | null>(null);
  const [directionsLoading, setDirectionsLoading] = useState(false);
  const [directionsError, setDirectionsError] = useState(false);

  const {
    data: vendorRes,
    isLoading: vendorLoading,
    error: vendorError,
  } = useQuery({
    queryKey: queryKeys.vendor.detail(vendorId!),
    queryFn: () => getVendorDetail(vendorId!),
    enabled: !!vendorId,
    staleTime: 5 * 60 * 1000,
  });

  const vendor = vendorRes?.data;
  const vendorLng = vendor?.location.coordinates[0];
  const vendorLat = vendor?.location.coordinates[1];

  // Fetch walking directions from Mapbox
  useEffect(() => {
    if (!currentLocation || vendorLng == null || vendorLat == null) return;
    let cancelled = false;
    setDirectionsLoading(true);
    setDirectionsError(false);
    fetchWalkingDirections(
      currentLocation.lng,
      currentLocation.lat,
      vendorLng,
      vendorLat,
    ).then((data) => {
      if (cancelled) return;
      if (data) {
        setDirections(data);
      } else {
        setDirectionsError(true);
      }
    }).catch(() => {
      if (!cancelled) setDirectionsError(true);
    }).finally(() => {
      if (!cancelled) setDirectionsLoading(false);
    });
    return () => { cancelled = true; };
  }, [currentLocation, vendorLng, vendorLat]);

  // Initialize Mapbox token
  useEffect(() => {
    if (import.meta.env.VITE_MAPBOX_TOKEN) {
      mapboxgl.accessToken = import.meta.env.VITE_MAPBOX_TOKEN;
    }
  }, []);

  // Initialize map when vendor and directions are available
  useEffect(() => {
    if (!mapContainer.current || !currentLocation || !vendor || !directions) return;

    if (!mapRef.current) {
      mapRef.current = new mapboxgl.Map({
        container: mapContainer.current,
        style: 'mapbox://styles/mapbox/streets-v12',
        center: [currentLocation.lng, currentLocation.lat],
        zoom: 16,
        pitch: 45,
        bearing: 0,
        antialias: true,
      });
      mapRef.current.addControl(new mapboxgl.NavigationControl(), 'top-right');
    }

    const m = mapRef.current;

    const onLoad = () => {
      if (m.getSource('route')) {
        (m.getSource('route') as mapboxgl.GeoJSONSource).setData({
          type: 'Feature',
          properties: {},
          geometry: directions.geometry,
        });
      } else {
        m.addSource('route', {
          type: 'geojson',
          data: {
            type: 'Feature',
            properties: {},
            geometry: directions.geometry,
          },
        });
        m.addLayer({
          id: 'route',
          type: 'line',
          source: 'route',
          layout: { 'line-join': 'round', 'line-cap': 'round' },
          paint: { 'line-color': getComputedStyle(document.documentElement).getPropertyValue('--brand-teal').trim() || '#0D9488', 'line-width': 6, 'line-opacity': 0.8 },
        });
      }

      new mapboxgl.Marker({ color: getComputedStyle(document.documentElement).getPropertyValue('--color-success').trim() || '#0D9488' })
        .setLngLat([currentLocation.lng, currentLocation.lat])
        .addTo(m);

      new mapboxgl.Marker({ color: getComputedStyle(document.documentElement).getPropertyValue('--brand-crimson').trim() || '#DC2626' })
        .setLngLat([vendor.location.coordinates[0], vendor.location.coordinates[1]])
        .addTo(m);

      const bounds = new mapboxgl.LngLatBounds();
      directions.geometry.coordinates.forEach((coord) => {
        bounds.extend(coord as [number, number]);
      });
      m.fitBounds(bounds, { padding: 50 });
    };

    if (m.loaded()) {
      onLoad();
    } else {
      m.on('load', onLoad);
    }
  }, [currentLocation, vendor, directions]);

  // Cleanup map on unmount
  useEffect(() => {
    return () => {
      mapRef.current?.remove();
      mapRef.current = null;
    };
  }, []);

  const startNavigation = useCallback(() => {
    if (directions) {
      setIsNavigating(true);
      setCurrentStep(0);
    }
  }, [directions]);

  const stopNavigation = useCallback(() => {
    setIsNavigating(false);
    setCurrentStep(0);
    if (vendorId) {
      recordArrival(vendorId);
    }
  }, [vendorId]);

  const nextStep = useCallback(() => {
    if (directions && currentStep < directions.steps.length - 1) {
      setCurrentStep((s) => s + 1);
    }
  }, [currentStep, directions]);

  const prevStep = useCallback(() => {
    if (currentStep > 0) {
      setCurrentStep((s) => s - 1);
    }
  }, [currentStep]);

  const toggleFullscreen = useCallback(() => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen();
      setIsFullscreen(true);
    } else {
      document.exitFullscreen();
      setIsFullscreen(false);
    }
  }, []);

  const speakDirection = useCallback((text: string) => {
    if (!isMuted && 'speechSynthesis' in window) {
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 0.9;
      speechSynthesis.speak(utterance);
    }
  }, [isMuted]);

  useEffect(() => {
    if (isNavigating && directions?.steps[currentStep]) {
      speakDirection(directions.steps[currentStep].instruction);
    }
  }, [currentStep, isNavigating, directions, speakDirection]);

  const formatDuration = (seconds: number) => {
    if (seconds < 60) return `${Math.round(seconds)}s`;
    return `${Math.round(seconds / 60)} min`;
  };

  if (vendorLoading || directionsLoading) {
    return (
      <div className={styles.page}>
        <div className={styles.loadingContainer}>
          <div className={styles.spinner} />
          <p>Loading navigation…</p>
        </div>
      </div>
    );
  }

  if (vendorError || directionsError || !vendor) {
    return (
      <div className={styles.page}>
        <header className={styles.topBar}>
          <Link to={`/vendor/${vendorId}`} className={styles.backBtn} aria-label="Back">
            <ArrowLeft size={20} />
          </Link>
          <h1 className={styles.title}>Navigation</h1>
        </header>
        <main className={styles.content} id="main-content">
          <div className={styles.errorState}>
            <AlertCircle size={48} />
            <h2>Navigation unavailable</h2>
            <p>Unable to load directions. Please try again.</p>
            <Link to={`/vendor/${vendorId}`} className={styles.retryBtn}>
              Back to Vendor
            </Link>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <header className={styles.topBar}>
        <Link to={`/vendor/${vendorId}`} className={styles.backBtn} aria-label="Back">
          <ArrowLeft size={20} />
        </Link>
        <h1 className={styles.title}>
          {isNavigating ? 'Navigating' : 'Directions'}
        </h1>
        <div className={styles.headerActions}>
          <button 
            className={styles.actionBtn}
            onClick={() => setIsMuted(!isMuted)}
            aria-label={isMuted ? 'Unmute' : 'Mute'}
          >
            {isMuted ? <VolumeX size={18} /> : <Volume2 size={18} />}
          </button>
          <button 
            className={styles.actionBtn}
            onClick={toggleFullscreen}
            aria-label={isFullscreen ? 'Exit fullscreen' : 'Fullscreen'}
          >
            {isFullscreen ? <Minimize2 size={18} /> : <Maximize2 size={18} />}
          </button>
        </div>
      </header>

      <main className={styles.content} id="main-content">
        {/* Map Container */}
        <div className={styles.mapContainer}>
          <div ref={mapContainer} className={styles.map} />
        </div>

        {/* Navigation Info */}
        <div className={styles.navigationPanel}>
          {!isNavigating ? (
            <div className={styles.directionsSummary}>
              <div className={styles.routeInfo}>
                <h2>{vendor.business_name}</h2>
                <p>{vendor.address}, {vendor.area}</p>
              </div>
              
              {directions && (
                <>
                  <div className={styles.routeStats}>
                    <div className={styles.stat}>
                      <Footprints size={20} />
                      <div>
                        <span className={styles.statValue}>{formatDistance(directions.distance / 1000)}</span>
                        <span className={styles.statLabel}>Distance</span>
                      </div>
                    </div>
                    <div className={styles.stat}>
                      <Clock size={20} />
                      <div>
                        <span className={styles.statValue}>{formatDuration(directions.duration)}</span>
                        <span className={styles.statLabel}>Walking</span>
                      </div>
                    </div>
                  </div>

                  <button 
                    className={styles.startBtn}
                    onClick={startNavigation}
                  >
                    <Navigation2 size={20} />
                    Start Navigation
                  </button>
                </>
              )}
            </div>
          ) : directions ? (
            <div className={styles.activeNavigation}>
              <div className={styles.currentStep}>
                <div className={styles.stepInstruction}>
                  <h3>{directions.steps[currentStep].instruction}</h3>
                  <p>{formatDistance(directions.steps[currentStep].distance / 1000)}</p>
                </div>
                
                <div className={styles.stepVisual}>
                  <div className={styles.stepIcon}>
                    {directions.steps[currentStep].maneuver.includes('left') && '↰'}
                    {directions.steps[currentStep].maneuver.includes('right') && '↱'}
                    {directions.steps[currentStep].maneuver === 'depart' && '🚶'}
                    {directions.steps[currentStep].maneuver === 'arrive' && '🎯'}
                    {directions.steps[currentStep].maneuver === 'continue' && '↑'}
                  </div>
                </div>
              </div>

              <div className={styles.navigationControls}>
                <button 
                  className={styles.controlBtn}
                  onClick={prevStep}
                  disabled={currentStep === 0}
                >
                  Previous
                </button>
                <span className={styles.stepCounter}>
                  {currentStep + 1} / {directions.steps.length}
                </span>
                <button 
                  className={styles.controlBtn}
                  onClick={nextStep}
                  disabled={currentStep === directions.steps.length - 1}
                >
                  Next
                </button>
              </div>

              <button 
                className={styles.stopBtn}
                onClick={stopNavigation}
              >
                <RotateCcw size={18} />
                End Navigation
              </button>
            </div>
          ) : null}
        </div>
      </main>
    </div>
  );
}
