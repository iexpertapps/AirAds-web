import { useState, useRef, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { 
  ArrowLeft, 
  Film, 
  Heart, 
  Share2, 
  Play,
  Volume2,
  VolumeX,
  Eye,
  Clock
} from 'lucide-react';
import { getReelsFeed, recordReelView } from '@/api/reels';
import { queryKeys } from '@/queryKeys';
import { formatCount, formatTimeAgo } from '@/utils/formatters';
import { TierBadge } from '@/components/dls/TierBadge';
import { useLocation } from '@/hooks/useLocation';
import type { VendorReel } from '@/types/api';
import styles from './ReelsPage.module.css';

export default function ReelsPage() {
  const { location } = useLocation();
  const [currentReelIndex, setCurrentReelIndex] = useState(0);
  const [isMuted, setIsMuted] = useState(true);
  const [isPlaying, setIsPlaying] = useState(true);
  const containerRef = useRef<HTMLDivElement>(null);
  const videoRefs = useRef<(HTMLVideoElement | null)[]>([]);
  const viewedReels = useRef<Set<string>>(new Set());

  const {
    data: reelsRes,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: queryKeys.reels.feed(location?.lat ?? 0, location?.lng ?? 0),
    queryFn: () => getReelsFeed(location!.lat, location!.lng),
    enabled: !!location,
    staleTime: 1 * 60 * 1000,
  });

  const reels: VendorReel[] = reelsRes?.data ?? [];

  const playVideo = useCallback((index: number) => {
    const video = videoRefs.current[index];
    if (video) {
      video.play().catch(() => {
        setIsPlaying(false);
      });
    }
  }, []);

  const pauseVideo = useCallback((index: number) => {
    const video = videoRefs.current[index];
    if (video) {
      video.pause();
    }
  }, []);

  const trackView = useCallback((reelId: string) => {
    if (!viewedReels.current.has(reelId)) {
      viewedReels.current.add(reelId);
      recordReelView(reelId);
    }
  }, []);

  const handleScroll = useCallback(() => {
    if (!containerRef.current) return;

    const container = containerRef.current;
    const scrollTop = container.scrollTop;
    const itemHeight = container.clientHeight;
    const newIndex = Math.round(scrollTop / itemHeight);

    if (newIndex !== currentReelIndex && newIndex >= 0 && newIndex < reels.length) {
      pauseVideo(currentReelIndex);
      setCurrentReelIndex(newIndex);
      playVideo(newIndex);
      trackView(reels[newIndex].id);
    }
  }, [currentReelIndex, reels, playVideo, pauseVideo, trackView]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    container.addEventListener('scroll', handleScroll);
    return () => container.removeEventListener('scroll', handleScroll);
  }, [handleScroll]);

  useEffect(() => {
    if (reels.length > 0 && isPlaying) {
      playVideo(0);
      trackView(reels[0].id);
    }
  }, [reels.length, isPlaying, playVideo, trackView, reels]);

  const togglePlayPause = useCallback(() => {
    if (isPlaying) {
      pauseVideo(currentReelIndex);
    } else {
      playVideo(currentReelIndex);
    }
    setIsPlaying(!isPlaying);
  }, [isPlaying, currentReelIndex, playVideo, pauseVideo]);

  const toggleMute = useCallback(() => {
    const video = videoRefs.current[currentReelIndex];
    if (video) {
      video.muted = !isMuted;
      setIsMuted(!isMuted);
    }
  }, [currentReelIndex, isMuted]);

  const handleShare = useCallback(async (reel: VendorReel) => {
    if (navigator.share) {
      try {
        await navigator.share({
          title: `${reel.title} — ${reel.vendor_name}`,
          url: `${window.location.origin}/reels`,
        });
      } catch {
        // user cancelled
      }
    }
  }, []);

  if (isLoading) {
    return (
      <div className={styles.page}>
        <div className={styles.loadingContainer}>
          <div className={styles.spinner} />
          <p>Loading reels…</p>
        </div>
      </div>
    );
  }

  if (error || reels.length === 0) {
    return (
      <div className={styles.page}>
        <header className={styles.topBar}>
          <Link to="/discover" className={styles.backBtn} aria-label="Back">
            <ArrowLeft size={20} />
          </Link>
          <h1 className={styles.title}>Reels</h1>
        </header>
        <main className={styles.content} id="main-content">
          <div className={styles.emptyState}>
            <Film size={48} />
            <h2>No reels available</h2>
            <p>Check back later for new content from local vendors</p>
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
      {/* Header Overlay */}
      <header className={styles.topBarOverlay}>
        <Link to="/discover" className={styles.backBtn} aria-label="Back">
          <ArrowLeft size={20} />
        </Link>
        <h1 className={styles.title}>Reels</h1>
      </header>

      {/* Reels Feed Container */}
      <div 
        ref={containerRef}
        className={styles.reelsContainer}
      >
        {reels.map((reel, index) => (
          <div 
            key={reel.id}
            className={styles.reelItem}
          >
            {/* Video Background */}
            <video
              ref={(el) => { videoRefs.current[index] = el; }}
              src={reel.video_url}
              className={styles.reelVideo}
              loop
              playsInline
              muted={isMuted}
              onClick={togglePlayPause}
              poster={reel.thumbnail_url ?? undefined}
            />

            {/* Video Overlay */}
            <div className={styles.reelOverlay}>
              {!isPlaying && index === currentReelIndex && (
                <div className={styles.playIndicator}>
                  <Play size={64} />
                </div>
              )}

              {/* Right Side Actions */}
              <div className={styles.sideActions}>
                <button className={styles.actionBtn} aria-label="Like">
                  <Heart size={24} />
                </button>
                
                <button 
                  className={styles.actionBtn}
                  onClick={() => handleShare(reel)}
                  aria-label="Share"
                >
                  <Share2 size={24} />
                </button>
              </div>

              {/* Bottom Content */}
              <div className={styles.reelContent}>
                <Link to={`/vendor/${reel.vendor_id}`} className={styles.vendorInfo}>
                  <div className={styles.vendorAvatar}>
                    {reel.vendor_logo_url ? (
                      <img src={reel.vendor_logo_url} alt={reel.vendor_name} />
                    ) : (
                      <div className={styles.avatarPlaceholder}>
                        {reel.vendor_name.charAt(0)}
                      </div>
                    )}
                  </div>
                  <div className={styles.vendorDetails}>
                    <h3 className={styles.vendorName}>{reel.vendor_name}</h3>
                    <TierBadge tier={reel.vendor_tier} />
                  </div>
                </Link>

                <p className={styles.reelCaption}>{reel.title}</p>

                <div className={styles.reelMeta}>
                  <div className={styles.metaItem}>
                    <Eye size={14} />
                    <span>{formatCount(reel.view_count)}</span>
                  </div>
                  <div className={styles.metaItem}>
                    <Clock size={14} />
                    <span>{formatTimeAgo(reel.created_at)}</span>
                  </div>
                </div>

                {/* Progress Bar */}
                <div className={styles.progressBar}>
                  <div 
                    className={styles.progressFill}
                    style={{ '--progress': `${((index + 1) / reels.length) * 100}%` } as React.CSSProperties}
                  />
                </div>
              </div>

              {/* Video Controls */}
              <div className={styles.videoControls}>
                <button 
                  className={styles.controlBtn}
                  onClick={toggleMute}
                  aria-label={isMuted ? 'Unmute' : 'Mute'}
                >
                  {isMuted ? <VolumeX size={20} /> : <Volume2 size={20} />}
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
