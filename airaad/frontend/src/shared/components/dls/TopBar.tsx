import { LogOut, User, Sun, Moon } from 'lucide-react';
import { useUser } from '@/features/auth/store/authStore';
import { AuthStateManager } from '@/features/auth/store/authStore';
import { useUIStore } from '@/shared/store/uiStore';
import { queryClient } from '@/lib/queryClient';
import { apiClient } from '@/lib/axios';
import { Button } from '@/shared/components/dls/Button';
import { formatRole } from '@/shared/utils/formatters';
import styles from './TopBar.module.css';

interface TopBarProps {
  title?: string | undefined;
}

export function TopBar({ title }: TopBarProps) {
  const user = useUser();
  const addToast = useUIStore((s) => s.addToast);
  const theme = useUIStore((s) => s.theme);
  const toggleTheme = useUIStore((s) => s.toggleTheme);

  async function handleLogout() {
    try {
      await apiClient.post('/api/v1/auth/logout/');
    } catch {
      // best-effort — proceed even if server call fails
    } finally {
      AuthStateManager.logout();
      queryClient.clear();
      addToast({ type: 'info', message: 'You have been signed out.' });
      window.location.href = '/login';
    }
  }

  return (
    <header className={styles.topbar} role="banner">
      {title && <h1 className={styles.title}>{title}</h1>}
      <div className={styles.spacer} aria-hidden="true" />
      <div className={styles.actions}>
        {user && (
          <div className={styles.userInfo} aria-label={`Signed in as ${user.full_name ?? user.email}`}>
            <span className={styles.avatar} aria-hidden="true">
              <User size={16} strokeWidth={1.5} />
            </span>
            <span className={styles.userName}>{user.full_name ?? user.email}</span>
            <span className={styles.userRole}>{formatRole(user.role)}</span>
          </div>
        )}
        <button
          className={styles.themeToggle}
          onClick={toggleTheme}
          aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
          aria-pressed={theme === 'dark'}
        >
          {theme === 'dark' ? (
            <Sun size={16} strokeWidth={1.5} aria-hidden="true" />
          ) : (
            <Moon size={16} strokeWidth={1.5} aria-hidden="true" />
          )}
        </button>
        <Button
          variant="ghost"
          size="compact"
          leftIcon={<LogOut size={16} strokeWidth={1.5} />}
          onClick={handleLogout}
          aria-label="Sign out"
        >
          Sign out
        </Button>
      </div>
    </header>
  );
}
