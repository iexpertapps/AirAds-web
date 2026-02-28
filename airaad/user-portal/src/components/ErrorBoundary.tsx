import { Component, type ErrorInfo, type ReactNode } from 'react';
import { Home, RefreshCw } from 'lucide-react';
import styles from './ErrorBoundary.module.css';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class GlobalErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    if (import.meta.env.DEV) {
      // eslint-disable-next-line no-console
      console.error('[AirAd ErrorBoundary]', error, info.componentStack);
    }
  }

  handleRetry = (): void => {
    this.setState({ hasError: false, error: null });
  };

  handleGoHome = (): void => {
    window.location.href = '/';
  };

  render(): ReactNode {
    if (!this.state.hasError) return this.props.children;

    return (
      <div className={styles.page}>
        <div className={styles.container}>
          <img src="/airad_icon.png" alt="AirAd" className={styles.logo} />
          <h1 className={styles.heading}>Something went wrong</h1>
          <p className={styles.message}>
            An unexpected error occurred. Please try refreshing the page.
          </p>
          <div className={styles.actions}>
            <button onClick={this.handleRetry} className={styles.primaryBtn}>
              <RefreshCw size={16} />
              Try Again
            </button>
            <button onClick={this.handleGoHome} className={styles.secondaryBtn}>
              <Home size={16} />
              Go Home
            </button>
          </div>
        </div>
      </div>
    );
  }
}
