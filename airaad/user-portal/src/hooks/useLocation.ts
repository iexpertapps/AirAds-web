import { useEffect, useCallback, useRef } from 'react';
import { useDiscoveryStore } from '@/store/discoveryStore';

export function useLocation() {
  const setLocation = useDiscoveryStore((s) => s.setLocation);
  const setLocationError = useDiscoveryStore((s) => s.setLocationError);
  const setLocationPermission = useDiscoveryStore((s) => s.setLocationPermission);
  const location = useDiscoveryStore((s) => s.location);
  const locationError = useDiscoveryStore((s) => s.locationError);
  const locationPermission = useDiscoveryStore((s) => s.locationPermission);
  const watchIdRef = useRef<number | null>(null);

  const requestLocation = useCallback(() => {
    if (!navigator.geolocation) {
      setLocationError('Geolocation is not supported by your browser');
      setLocationPermission('denied');
      return;
    }

    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLocation({
          lat: pos.coords.latitude,
          lng: pos.coords.longitude,
          accuracy: pos.coords.accuracy,
          heading: pos.coords.heading,
          timestamp: pos.timestamp,
        });
        setLocationPermission('granted');
      },
      (err) => {
        switch (err.code) {
          case err.PERMISSION_DENIED:
            setLocationError('Location permission denied. Please enable location access.');
            setLocationPermission('denied');
            break;
          case err.POSITION_UNAVAILABLE:
            setLocationError('Location unavailable. Please try again.');
            break;
          case err.TIMEOUT:
            setLocationError('Location request timed out. Please try again.');
            break;
        }
      },
      {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 30000,
      },
    );
  }, [setLocation, setLocationError, setLocationPermission]);

  const startWatching = useCallback(() => {
    if (!navigator.geolocation) return;
    if (watchIdRef.current !== null) return;

    watchIdRef.current = navigator.geolocation.watchPosition(
      (pos) => {
        setLocation({
          lat: pos.coords.latitude,
          lng: pos.coords.longitude,
          accuracy: pos.coords.accuracy,
          heading: pos.coords.heading,
          timestamp: pos.timestamp,
        });
      },
      () => {
        // silent fail on watch updates
      },
      {
        enableHighAccuracy: true,
        timeout: 15000,
        maximumAge: 5000,
      },
    );
  }, [setLocation]);

  const stopWatching = useCallback(() => {
    if (watchIdRef.current !== null) {
      navigator.geolocation.clearWatch(watchIdRef.current);
      watchIdRef.current = null;
    }
  }, []);

  useEffect(() => {
    return () => {
      stopWatching();
    };
  }, [stopWatching]);

  return {
    location,
    locationError,
    locationPermission,
    requestLocation,
    startWatching,
    stopWatching,
  };
}
