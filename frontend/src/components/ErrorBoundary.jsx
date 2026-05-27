import React from 'react';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    // Update state so the next render will show the fallback UI.
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    // You can also log the error to an error reporting service
    console.error("ErrorBoundary caught an error", error, errorInfo);
    this.setState({ error, errorInfo });
  }

  render() {
    if (this.state.hasError) {
      // You can render any custom fallback UI
      return (
        <div style={{
          display: 'flex', 
          flexDirection: 'column', 
          alignItems: 'center', 
          justifyContent: 'center', 
          padding: '40px 20px', 
          textAlign: 'center',
          minHeight: '300px',
          backgroundColor: 'var(--bg-color)',
          color: 'var(--text-color)',
          borderRadius: '12px',
          border: '1px solid rgba(255,255,255,0.1)',
          margin: '20px auto',
          maxWidth: '600px'
        }}>
          <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>⚠️</div>
          <h2 style={{ marginBottom: '1rem', color: '#ef4444' }}>Something went wrong.</h2>
          <p style={{ color: 'var(--text-dim)', marginBottom: '1.5rem' }}>
            We encountered an unexpected error while loading this component.
          </p>
          <button 
            onClick={() => window.location.reload()}
            style={{
              padding: '10px 20px',
              backgroundColor: 'var(--primary)',
              color: '#fff',
              border: 'none',
              borderRadius: '8px',
              cursor: 'pointer',
              fontWeight: '600'
            }}
          >
            Refresh Page
          </button>
          
          {process.env.NODE_ENV === 'development' && this.state.error && (
            <details style={{ marginTop: '2rem', textAlign: 'left', background: 'rgba(0,0,0,0.2)', padding: '15px', borderRadius: '8px', maxWidth: '100%', overflowX: 'auto' }}>
              <summary style={{ cursor: 'pointer', color: '#f87171' }}>Error Details (Dev Only)</summary>
              <pre style={{ color: '#fca5a5', marginTop: '10px', fontSize: '0.8rem', whiteSpace: 'pre-wrap' }}>
                {this.state.error.toString()}
                <br />
                {this.state.errorInfo?.componentStack}
              </pre>
            </details>
          )}
        </div>
      );
    }

    return this.props.children; 
  }
}

export default ErrorBoundary;
