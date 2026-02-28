import { useState, useCallback } from 'react';
import { Outlet, NavLink, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard, User, Tag, Film, BarChart3,
  Mic, CreditCard, ChevronLeft, ChevronRight,
  LogOut, Sun, Moon, Menu,
} from 'lucide-react';
import { useAuthStore } from '@/store/authStore';
import { useUIStore } from '@/store/uiStore';
import styles from './PortalLayout.module.css';

interface NavItem {
  to: string;
  label: string;
  icon: React.ReactNode;
}

const NAV_ITEMS: NavItem[] = [
  { to: '/portal/dashboard', label: 'Dashboard', icon: <LayoutDashboard size={18} strokeWidth={1.5} /> },
  { to: '/portal/profile', label: 'Profile', icon: <User size={18} strokeWidth={1.5} /> },
  { to: '/portal/discounts', label: 'Discounts', icon: <Tag size={18} strokeWidth={1.5} /> },
  { to: '/portal/reels', label: 'Reels', icon: <Film size={18} strokeWidth={1.5} /> },
  { to: '/portal/analytics', label: 'Analytics', icon: <BarChart3 size={18} strokeWidth={1.5} /> },
  { to: '/portal/voice-bot', label: 'Voice Bot', icon: <Mic size={18} strokeWidth={1.5} /> },
  { to: '/portal/subscription', label: 'Subscription', icon: <CreditCard size={18} strokeWidth={1.5} /> },
];

export function PortalLayout() {
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);
  const collapsed = useUIStore((s) => s.sidebarCollapsed);
  const toggleSidebar = useUIStore((s) => s.toggleSidebar);
  const theme = useUIStore((s) => s.theme);
  const toggleTheme = useUIStore((s) => s.toggleTheme);
  const [mobileOpen, setMobileOpen] = useState(false);

  const handleLogout = useCallback(() => {
    logout();
    navigate('/login', { replace: true });
  }, [logout, navigate]);

  const closeMobile = useCallback(() => setMobileOpen(false), []);

  const tier = user?.subscription_level ?? 'SILVER';

  const sidebarClasses = [
    styles.sidebar,
    collapsed ? styles['sidebar--collapsed'] : '',
    mobileOpen ? styles['sidebar--open'] : '',
  ].filter(Boolean).join(' ');

  return (
    <div className={styles.layout}>
      {mobileOpen && (
        <div className={styles.overlay} onClick={closeMobile} aria-hidden="true" />
      )}

      <aside className={sidebarClasses} aria-label="Portal navigation">
        <div className={styles.sidebarHeader}>
          <div className={styles.logoWrap}>
            <img src="/airad_icon.png" alt="AirAd" className={styles.logoIcon} />
            <span className={styles.logoText}>AirAd</span>
          </div>
          <button
            className={styles.collapseBtn}
            onClick={toggleSidebar}
            aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {collapsed ? <ChevronRight size={16} strokeWidth={1.5} /> : <ChevronLeft size={16} strokeWidth={1.5} />}
          </button>
        </div>

        <nav>
          <ul className={styles.navList}>
            {NAV_ITEMS.map((item) => (
              <li key={item.to}>
                <NavLink
                  to={item.to}
                  className={({ isActive }) =>
                    [styles.navItem, isActive ? styles['navItem--active'] : ''].join(' ')
                  }
                  onClick={closeMobile}
                >
                  <span className={styles.navIcon}>{item.icon}</span>
                  <span className={styles.navLabel}>{item.label}</span>
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>

        <div className={styles.sidebarFooter}>
          <div className={[styles.tierBadge, styles[`tierBadge--${tier}`]].join(' ')}>
            <CreditCard size={12} strokeWidth={1.5} />
            <span>{tier}</span>
          </div>
        </div>
      </aside>

      <div className={[styles.main, collapsed ? styles['main--collapsed'] : ''].join(' ')}>
        <header className={styles.topbar}>
          <div className={styles.topbarLeft}>
            <button
              className={[styles.topbarBtn, styles.mobileMenuBtn].join(' ')}
              onClick={() => setMobileOpen(true)}
              aria-label="Open menu"
            >
              <Menu size={20} strokeWidth={1.5} />
            </button>
            <span className={styles.topbarTitle}>
              {user?.full_name ? `Hello, ${user.full_name}` : 'Vendor Portal'}
            </span>
          </div>

          <div className={styles.topbarActions}>
            <button
              className={styles.topbarBtn}
              onClick={toggleTheme}
              aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
            >
              {theme === 'dark' ? <Sun size={18} strokeWidth={1.5} /> : <Moon size={18} strokeWidth={1.5} />}
            </button>
            <button
              className={styles.topbarBtn}
              onClick={handleLogout}
              aria-label="Log out"
            >
              <LogOut size={18} strokeWidth={1.5} />
            </button>
          </div>
        </header>

        <div id="main-content" className={styles.content}>
          <Outlet />
        </div>
      </div>
    </div>
  );
}
