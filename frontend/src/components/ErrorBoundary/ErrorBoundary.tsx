import React, { Component, ErrorInfo, ReactNode } from 'react';
import { Button } from '../UI';

interface Props {
  children: ReactNode;
  fallback?: (error: Error, errorInfo: ErrorInfo) => ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
}

interface State {
  hasError: boolean;
  error?: Error;
  errorInfo?: ErrorInfo;
  errorId?: string;
}

class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): State {
    const errorId = `ERR_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    return { hasError: true, error, errorId };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    const errorId = this.state.errorId || 'unknown';
    
    // Enhanced error logging with categorization
    const errorDetails = {
      errorId,
      message: error.message,
      stack: error.stack,
      componentStack: errorInfo.componentStack,
      timestamp: new Date().toISOString(),
      userAgent: navigator.userAgent,
      url: window.location.href,
      errorType: this.categorizeError(error)
    };

    // Log to console with structured data
    console.group(`🚨 ErrorBoundary: ${errorDetails.errorType}`);
    console.error('Error:', error);
    console.error('Error Info:', errorInfo);
    console.error('Error Details:', errorDetails);
    console.groupEnd();

    // Send to error logging service (if available)
    this.logErrorToService(errorDetails);

    // Call custom error handler if provided
    if (this.props.onError) {
      this.props.onError(error, errorInfo);
    }

    this.setState({ error, errorInfo });
  }

  private categorizeError(error: Error): string {
    const message = error.message.toLowerCase();
    const stack = error.stack?.toLowerCase() || '';

    if (message.includes('network') || message.includes('fetch')) {
      return 'Network Error';
    }
    if (message.includes('chunk') || stack.includes('chunk')) {
      return 'Code Splitting Error';
    }
    if (message.includes('permission') || message.includes('cors')) {
      return 'Permission Error';
    }
    if (stack.includes('react') || stack.includes('component')) {
      return 'React Component Error';
    }
    if (message.includes('timeout')) {
      return 'Timeout Error';
    }
    
    return 'Application Error';
  }

  private async logErrorToService(errorDetails: any) {
    try {
      // In a real application, you would send this to your error logging service
      // For now, we'll just store it in localStorage for debugging
      const existingErrors = JSON.parse(localStorage.getItem('stackdebt_errors') || '[]');
      existingErrors.push(errorDetails);
      
      // Keep only the last 10 errors to avoid storage bloat
      if (existingErrors.length > 10) {
        existingErrors.splice(0, existingErrors.length - 10);
      }
      
      localStorage.setItem('stackdebt_errors', JSON.stringify(existingErrors));
    } catch (e) {
      console.warn('Failed to log error to service:', e);
    }
  }

  handleReset = () => {
    this.setState({ hasError: false, error: undefined, errorInfo: undefined, errorId: undefined });
  };

  handleReload = () => {
    window.location.reload();
  };

  handleReportError = () => {
    const errorDetails = {
      errorId: this.state.errorId,
      message: this.state.error?.message,
      timestamp: new Date().toISOString(),
      url: window.location.href
    };

    // Create a mailto link with error details
    const subject = encodeURIComponent(`StackDebt Error Report - ${this.state.errorId}`);
    const body = encodeURIComponent(`
Error Details:
- Error ID: ${errorDetails.errorId}
- Message: ${errorDetails.message}
- URL: ${errorDetails.url}
- Timestamp: ${errorDetails.timestamp}

Please describe what you were doing when this error occurred:
[Your description here]
    `);

    window.open(`mailto:support@stackdebt.app?subject=${subject}&body=${body}`);
  };

  render() {
    if (this.state.hasError) {
      // Use custom fallback if provided
      if (this.props.fallback && this.state.error && this.state.errorInfo) {
        return this.props.fallback(this.state.error, this.state.errorInfo);
      }

      const errorType = this.state.error ? this.categorizeError(this.state.error) : 'Unknown Error';

      return (
        <div className="min-h-screen bg-gray-900 text-terminal-green font-mono flex items-center justify-center">
          <div className="max-w-2xl mx-auto p-8">
            <div className="bg-gray-800 border border-terminal-red rounded-lg p-8 text-center">
              <div className="text-6xl mb-4">💥</div>
              
              <h1 className="text-2xl font-bold text-terminal-red mb-2">
                {errorType}
              </h1>
              
              <p className="text-gray-400 mb-6">
                The StackDebt analyzer encountered an unexpected error. 
                This incident has been logged for debugging.
              </p>

              {/* Error ID for support */}
              {this.state.errorId && (
                <div className="bg-gray-900 border border-gray-600 rounded p-3 mb-6">
                  <div className="text-sm text-gray-400 mb-1">Error ID:</div>
                  <div className="font-mono text-terminal-amber text-sm">
                    {this.state.errorId}
                  </div>
                </div>
              )}

              {/* User-friendly error message */}
              {this.state.error && (
                <div className="bg-gray-900 border border-terminal-amber/30 rounded p-4 mb-6 text-left">
                  <h3 className="text-terminal-amber font-semibold mb-2">What happened:</h3>
                  <p className="text-gray-300 text-sm">
                    {this.getUserFriendlyMessage(errorType, this.state.error.message)}
                  </p>
                </div>
              )}
              
              {/* Debug information (development only) */}
              {process.env.NODE_ENV === 'development' && this.state.error && (
                <div className="bg-gray-900 border border-gray-600 rounded p-4 mb-6 text-left">
                  <h3 className="text-terminal-amber font-semibold mb-2">Debug Information:</h3>
                  <pre className="text-xs text-gray-300 overflow-auto max-h-32">
                    {this.state.error.toString()}
                    {this.state.errorInfo?.componentStack}
                  </pre>
                </div>
              )}
              
              <div className="flex flex-col sm:flex-row gap-3 justify-center">
                <Button onClick={this.handleReset} variant="primary">
                  Try Again
                </Button>
                <Button onClick={this.handleReload} variant="secondary">
                  Reload Application
                </Button>
                <Button onClick={this.handleReportError} variant="secondary" size="sm">
                  Report Error
                </Button>
              </div>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }

  private getUserFriendlyMessage(errorType: string, originalMessage: string): string {
    switch (errorType) {
      case 'Network Error':
        return 'There was a problem connecting to our servers. Please check your internet connection and try again.';
      case 'Code Splitting Error':
        return 'There was a problem loading part of the application. Refreshing the page should resolve this issue.';
      case 'Permission Error':
        return 'The application doesn\'t have the necessary permissions to complete this action.';
      case 'React Component Error':
        return 'A component in the application encountered an error while rendering.';
      case 'Timeout Error':
        return 'The operation took too long to complete. Please try again.';
      default:
        return 'An unexpected error occurred in the application. Our team has been notified.';
    }
  }
}

export default ErrorBoundary;