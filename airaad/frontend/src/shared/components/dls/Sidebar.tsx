import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  MapPin,
  Tag,
  Store,
  Upload,
  Camera,
  ShieldCheck,
  Shield,
  BookOpen,
  Users,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import { useUIStore } from '@/shared/store/uiStore';
import { useUserRole } from '@/features/auth/store/authStore';
import type { Role } from '@/features/auth/store/authStore';
import styles from './Sidebar.module.css';

interface NavItem {
  to: string;
  label: string;
  icon: React.ReactNode;
  allowedRoles: Role[];
}

const NAV_ITEMS: NavItem[] = [
  {
    to: '/',
    label: 'Dashboard',
    icon: <LayoutDashboard size={18} strokeWidth={1.5} />,
    allowedRoles: ['SUPER_ADMIN', 'CITY_MANAGER', 'ANALYST', 'QA_REVIEWER', 'FIELD_AGENT', 'SUPPORT', 'OPERATIONS_MANAGER', 'CONTENT_MODERATOR', 'DATA_QUALITY_ANALYST', 'ANALYTICS_OBSERVER'],
  },
  {
    to: '/geo',
    label: 'Geographic',
    icon: <MapPin size={18} strokeWidth={1.5} />,
    allowedRoles: ['SUPER_ADMIN', 'CITY_MANAGER', 'DATA_ENTRY'],
  },
  {
    to: '/tags',
    label: 'Tags',
    icon: <Tag size={18} strokeWidth={1.5} />,
    allowedRoles: ['SUPER_ADMIN', 'CITY_MANAGER', 'DATA_ENTRY', 'DATA_QUALITY_ANALYST'],
  },
  {
    to: '/vendors',
    label: 'Vendors',
    icon: <Store size={18} strokeWidth={1.5} />,
    allowedRoles: ['SUPER_ADMIN', 'CITY_MANAGER', 'DATA_ENTRY', 'QA_REVIEWER', 'SUPPORT'],
  },
  {
    to: '/imports',
    label: 'Imports',
    icon: <Upload size={18} strokeWidth={1.5} />,
    allowedRoles: ['SUPER_ADMIN', 'CITY_MANAGER', 'DATA_ENTRY', 'OPERATIONS_MANAGER'],
  },
  {
    to: '/field-ops',
    label: 'Field Ops',
    icon: <Camera size={18} strokeWidth={1.5} />,
    allowedRoles: ['SUPER_ADMIN', 'CITY_MANAGER', 'FIELD_AGENT'],
  },
  {
    to: '/qa',
    label: 'QA Dashboard',
    icon: <ShieldCheck size={18} strokeWidth={1.5} />,
    allowedRoles: ['SUPER_ADMIN', 'CITY_MANAGER', 'QA_REVIEWER'],
  },
  {
    to: '/governance',
    label: 'Governance',
    icon: <Shield size={18} strokeWidth={1.5} />,
    allowedRoles: ['SUPER_ADMIN', 'OPERATIONS_MANAGER', 'CONTENT_MODERATOR'],
  },
  {
    to: '/system/audit',
    label: 'Audit Log',
    icon: <BookOpen size={18} strokeWidth={1.5} />,
    allowedRoles: ['SUPER_ADMIN', 'ANALYST', 'OPERATIONS_MANAGER'],
  },
  {
    to: '/system/users',
    label: 'Users',
    icon: <Users size={18} strokeWidth={1.5} />,
    allowedRoles: ['SUPER_ADMIN'],
  },
];

export function Sidebar() {
  const collapsed = useUIStore((s) => s.sidebarCollapsed);
  const toggleSidebar = useUIStore((s) => s.toggleSidebar);
  const userRole = useUserRole();

  const visibleItems = NAV_ITEMS.filter(
    (item) => userRole !== undefined && item.allowedRoles.includes(userRole),
  );

  return (
    <nav
      className={[styles.sidebar, collapsed ? styles.collapsed : ''].join(' ')}
      aria-label="Main navigation"
    >
      <div className={styles.logo} aria-label="AirAd Admin">
        <div className={styles.logoIconWrap} aria-hidden="true">
          <img src="/airad_icon.png" alt="" className={styles.logoImg} />
        </div>
        {!collapsed && <span className={styles.logoText}>AirAd</span>}
      </div>

      <ul className={styles.navList} role="list">
        {visibleItems.map((item) => (
          <li key={item.to}>
            <NavLink
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) =>
                [styles.navItem, isActive ? styles.navItemActive : ''].join(' ')
              }
              aria-label={collapsed ? item.label : undefined}
            >
              <span className={styles.navIcon} aria-hidden="true">
                {item.icon}
              </span>
              {!collapsed && <span className={styles.navLabel}>{item.label}</span>}
            </NavLink>
          </li>
        ))}
      </ul>

      <button
        className={styles.collapseBtn}
        onClick={toggleSidebar}
        aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        aria-expanded={!collapsed}
      >
        {collapsed ? (
          <ChevronRight size={16} strokeWidth={1.5} aria-hidden="true" />
        ) : (
          <ChevronLeft size={16} strokeWidth={1.5} aria-hidden="true" />
        )}
      </button>
    </nav>
  );
}
