import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { 
  ArrowLeft, 
  Moon, 
  Sun, 
  Bell, 
  BellOff,
  MapPin,
  Eye,
  EyeOff,
  Smartphone,
  Mail,
  HelpCircle,
  Info,
  ChevronRight,
  Trash2,
  Download,
  Clock,
  AlertTriangle
} from 'lucide-react';
import { useAuthStore } from '@/store/authStore';
import { useUIStore } from '@/store/uiStore';
import { usePreferencesStore } from '@/store/preferencesStore';
import { getUserPreferences, clearSearchHistory, requestDataExport, requestAccountDeletion, requestDeletionCode } from '@/api/preferences';
import styles from './PreferencesPage.module.css';

export default function PreferencesPage() {
  const { user } = useAuthStore();
  const { theme, setTheme } = useUIStore();
  const { 
    searchRadius,
    notifications,
    locationSharing,
    dataCollection,
    setSearchRadius,
    setNotifications,
    setLocationSharing,
    setDataCollection
  } = usePreferencesStore();

  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const [saveMessage, setSaveMessage] = useState('');
  const [clearingHistory, setClearingHistory] = useState(false);
  const [exportingData, setExportingData] = useState(false);
  const [deletionCode, setDeletionCode] = useState('');
  const [deletionStep, setDeletionStep] = useState<'idle' | 'code_sent' | 'confirming'>('idle');

  // Sync preferences from backend on mount (M-25)
  useEffect(() => {
    if (!isAuthenticated) return;
    getUserPreferences()
      .then((res) => {
        if (res.success && res.data) {
          if (res.data.theme) setTheme(res.data.theme === 'system' ? 'dark' : res.data.theme);
        }
      })
      .catch(() => { /* fallback to local prefs */ });
  }, [isAuthenticated, setTheme]);

  // Handle theme toggle
  const handleThemeToggle = () => {
    const newTheme = theme === 'light' ? 'dark' : 'light';
    setTheme(newTheme);
    showSaveMessage('Theme updated');
  };

  // Handle radius change
  const handleRadiusChange = (value: number) => {
    setSearchRadius(value);
    showSaveMessage('Search radius updated');
  };

  // Handle notification toggle
  const handleNotificationToggle = (type: 'push' | 'email', enabled: boolean) => {
    setNotifications({
      ...notifications,
      [type]: enabled
    });
    showSaveMessage(`${type === 'push' ? 'Push' : 'Email'} notifications ${enabled ? 'enabled' : 'disabled'}`);
  };

  // Handle privacy toggle
  const handlePrivacyToggle = (setting: 'locationSharing' | 'dataCollection', enabled: boolean) => {
    if (setting === 'locationSharing') {
      setLocationSharing(enabled);
      showSaveMessage(`Location sharing ${enabled ? 'enabled' : 'disabled'}`);
    } else {
      setDataCollection(enabled);
      showSaveMessage(`Data collection ${enabled ? 'enabled' : 'disabled'}`);
    }
  };

  // Show save message
  const showSaveMessage = (message: string) => {
    setSaveMessage(message);
    setTimeout(() => setSaveMessage(''), 2000);
  };

  return (
    <div className={styles.page}>
      <header className={styles.topBar}>
        <Link to="/discover" className={styles.backBtn}>
          <ArrowLeft size={20} />
        </Link>
        <h1 className={styles.title}>Preferences</h1>
      </header>

      <main className={styles.content} id="main-content">
        {/* Save Message */}
        {saveMessage && (
          <div className={styles.saveMessage}>
            {saveMessage}
          </div>
        )}

        {/* Account Section */}
        <section className={styles.section}>
          <h2 className={styles.sectionTitle}>Account</h2>
          <div className={styles.settingGroup}>
            <div className={styles.settingItem}>
              <div className={styles.settingInfo}>
                <div className={styles.settingLabel}>Profile</div>
                <div className={styles.settingDescription}>
                  {user?.email || 'guest@airad.com'}
                </div>
              </div>
              <ChevronRight size={20} className={styles.chevron} />
            </div>
          </div>
        </section>

        {/* Appearance Section */}
        <section className={styles.section}>
          <h2 className={styles.sectionTitle}>Appearance</h2>
          <div className={styles.settingGroup}>
            <div className={styles.settingItem}>
              <div className={styles.settingInfo}>
                <div className={styles.settingLabel}>
                  {theme === 'light' ? <Sun size={18} /> : <Moon size={18} />}
                  Theme
                </div>
                <div className={styles.settingDescription}>
                  {theme === 'light' ? 'Light mode' : 'Dark mode'}
                </div>
              </div>
              <button 
                className={styles.toggleBtn}
                onClick={handleThemeToggle}
                aria-label="Toggle theme"
              >
                <div className={`${styles.toggleSlider} ${styles[theme]}`}>
                  {theme === 'light' ? <Sun size={14} /> : <Moon size={14} />}
                </div>
              </button>
            </div>
          </div>
        </section>

        {/* Search Settings */}
        <section className={styles.section}>
          <h2 className={styles.sectionTitle}>Search Settings</h2>
          <div className={styles.settingGroup}>
            <div className={styles.settingItem}>
              <div className={styles.settingInfo}>
                <div className={styles.settingLabel}>
                  <MapPin size={18} />
                  Search Radius
                </div>
                <div className={styles.settingDescription}>
                  {searchRadius} km from your location
                </div>
              </div>
            </div>
            <div className={styles.radiusSlider}>
              <input
                type="range"
                min="1"
                max="50"
                value={searchRadius}
                onChange={(e) => handleRadiusChange(Number(e.target.value))}
                className={styles.slider}
              />
              <div className={styles.sliderLabels}>
                <span>1 km</span>
                <span>50 km</span>
              </div>
            </div>
          </div>
        </section>

        {/* Notifications */}
        <section className={styles.section}>
          <h2 className={styles.sectionTitle}>Notifications</h2>
          <div className={styles.settingGroup}>
            <div className={styles.settingItem}>
              <div className={styles.settingInfo}>
                <div className={styles.settingLabel}>
                  <Smartphone size={18} />
                  Push Notifications
                </div>
                <div className={styles.settingDescription}>
                  Receive alerts on your device
                </div>
              </div>
              <button 
                className={styles.toggleBtn}
                onClick={() => handleNotificationToggle('push', !notifications.push)}
                aria-label="Toggle push notifications"
              >
                <div className={`${styles.toggleSlider} ${notifications.push ? styles.enabled : styles.disabled}`}>
                  {notifications.push ? <Bell size={14} /> : <BellOff size={14} />}
                </div>
              </button>
            </div>
            
            <div className={styles.settingItem}>
              <div className={styles.settingInfo}>
                <div className={styles.settingLabel}>
                  <Mail size={18} />
                  Email Notifications
                </div>
                <div className={styles.settingDescription}>
                  Receive updates via email
                </div>
              </div>
              <button 
                className={styles.toggleBtn}
                onClick={() => handleNotificationToggle('email', !notifications.email)}
                aria-label="Toggle email notifications"
              >
                <div className={`${styles.toggleSlider} ${notifications.email ? styles.enabled : styles.disabled}`}>
                  {notifications.email ? <Mail size={14} /> : <BellOff size={14} />}
                </div>
              </button>
            </div>
          </div>
        </section>

        {/* Privacy */}
        <section className={styles.section}>
          <h2 className={styles.sectionTitle}>Privacy</h2>
          <div className={styles.settingGroup}>
            <div className={styles.settingItem}>
              <div className={styles.settingInfo}>
                <div className={styles.settingLabel}>
                  <MapPin size={18} />
                  Location Sharing
                </div>
                <div className={styles.settingDescription}>
                  Allow app to access your location
                </div>
              </div>
              <button 
                className={styles.toggleBtn}
                onClick={() => handlePrivacyToggle('locationSharing', !locationSharing)}
                aria-label="Toggle location sharing"
              >
                <div className={`${styles.toggleSlider} ${locationSharing ? styles.enabled : styles.disabled}`}>
                  {locationSharing ? <Eye size={14} /> : <EyeOff size={14} />}
                </div>
              </button>
            </div>
            
            <div className={styles.settingItem}>
              <div className={styles.settingInfo}>
                <div className={styles.settingLabel}>
                  <Info size={18} />
                  Data Collection
                </div>
                <div className={styles.settingDescription}>
                  Help improve AirAd with usage data
                </div>
              </div>
              <button 
                className={styles.toggleBtn}
                onClick={() => handlePrivacyToggle('dataCollection', !dataCollection)}
                aria-label="Toggle data collection"
              >
                <div className={`${styles.toggleSlider} ${dataCollection ? styles.enabled : styles.disabled}`}>
                  {dataCollection ? <Info size={14} /> : <EyeOff size={14} />}
                </div>
              </button>
            </div>
          </div>
        </section>

        {/* Privacy & Data (M-15) — only for authenticated users */}
        {isAuthenticated && (
          <section className={styles.section}>
            <h2 className={styles.sectionTitle}>Privacy & Data</h2>
            <div className={styles.settingGroup}>
              <div className={styles.settingItem}>
                <div className={styles.settingInfo}>
                  <div className={styles.settingLabel}>
                    <Clock size={18} />
                    Search History
                  </div>
                  <div className={styles.settingDescription}>
                    Clear all your search history
                  </div>
                </div>
                <button
                  className={styles.dangerBtn}
                  disabled={clearingHistory}
                  onClick={async () => {
                    setClearingHistory(true);
                    try {
                      await clearSearchHistory();
                      showSaveMessage('Search history cleared');
                    } catch { showSaveMessage('Failed to clear history'); }
                    setClearingHistory(false);
                  }}
                >
                  <Trash2 size={14} />
                  {clearingHistory ? 'Clearing…' : 'Clear'}
                </button>
              </div>

              <div className={styles.settingItem}>
                <div className={styles.settingInfo}>
                  <div className={styles.settingLabel}>
                    <Download size={18} />
                    Export My Data
                  </div>
                  <div className={styles.settingDescription}>
                    Download all your data as a file
                  </div>
                </div>
                <button
                  className={styles.secondaryBtn}
                  disabled={exportingData}
                  onClick={async () => {
                    setExportingData(true);
                    try {
                      await requestDataExport();
                      showSaveMessage('Data export requested — check your email');
                    } catch { showSaveMessage('Export request failed'); }
                    setExportingData(false);
                  }}
                >
                  <Download size={14} />
                  {exportingData ? 'Requesting…' : 'Export'}
                </button>
              </div>

              <div className={styles.settingItem}>
                <div className={styles.settingInfo}>
                  <div className={styles.settingLabel}>
                    <AlertTriangle size={18} />
                    Delete Account
                  </div>
                  <div className={styles.settingDescription}>
                    Permanently delete your account and data
                  </div>
                </div>
                <button
                  className={styles.dangerBtn}
                  onClick={async () => {
                    if (deletionStep === 'idle') {
                      try {
                        await requestDeletionCode();
                        setDeletionStep('code_sent');
                        showSaveMessage('Verification code sent to your phone');
                      } catch { showSaveMessage('Failed to send code'); }
                    } else {
                      setDeletionStep('code_sent');
                    }
                  }}
                >
                  <Trash2 size={14} />
                  {deletionStep === 'idle' ? 'Delete' : 'Confirm Delete'}
                </button>
              </div>

              {deletionStep === 'code_sent' && (
                <div className={styles.deletionConfirm}>
                  <p>Enter the verification code sent to your phone:</p>
                  <input
                    type="text"
                    value={deletionCode}
                    onChange={(e) => setDeletionCode(e.target.value)}
                    placeholder="Enter code"
                    className={styles.codeInput}
                    maxLength={6}
                  />
                  <div className={styles.deletionActions}>
                    <button
                      className={styles.dangerBtn}
                      disabled={deletionCode.length < 4}
                      onClick={async () => {
                        try {
                          await requestAccountDeletion(deletionCode);
                          showSaveMessage('Account deletion confirmed');
                          setDeletionStep('idle');
                          setDeletionCode('');
                        } catch { showSaveMessage('Invalid code — try again'); }
                      }}
                    >
                      Confirm Deletion
                    </button>
                    <button
                      className={styles.secondaryBtn}
                      onClick={() => { setDeletionStep('idle'); setDeletionCode(''); }}
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              )}
            </div>
          </section>
        )}

        {/* Support */}
        <section className={styles.section}>
          <h2 className={styles.sectionTitle}>Support</h2>
          <div className={styles.settingGroup}>
            <div className={styles.settingItem}>
              <div className={styles.settingInfo}>
                <div className={styles.settingLabel}>
                  <HelpCircle size={18} />
                  Help Center
                </div>
                <div className={styles.settingDescription}>
                  Get help and support
                </div>
              </div>
              <ChevronRight size={20} className={styles.chevron} />
            </div>
            
            <div className={styles.settingItem}>
              <div className={styles.settingInfo}>
                <div className={styles.settingLabel}>
                  <Info size={18} />
                  About
                </div>
                <div className={styles.settingDescription}>
                  Version 1.0.0
                </div>
              </div>
              <ChevronRight size={20} className={styles.chevron} />
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
