import React from 'react';
import { Button } from '../UI';

export interface ErrorDisplayProps {
  error: {
    message: string;
    error?: string;
    suggestions?: string[];
    failed_detections?: string[];
    troubleshooting?: Record<string, any>;
    error_id?: string;
  };
  onRetry?: () => void;
  onReset?: () => void;
  variant?: 'inline' | 'page' | 'modal';
}

const ErrorDisplay: React.FC<ErrorDisplayProps> = ({ 
  error, 
  onRetry, 
  onReset, 
  variant = 'inline' 
}) => {
  const getErrorIcon = (errorType?: string) => {
    switch (errorType) {
      case 'RepositoryNotFound':
      case 'WebsiteNotFound':
        return '🔍';
      case 'AccessForbidden':
        return '🔒';
      case 'RateLimitExceeded':
        return '⏱️';
      case 'TimeoutError':
        return '⏰';
      case 'NetworkError':
        return '🌐';
      case 'NoComponentsDetected':
        return '📦';
      case 'ValidationError':
        return '⚠️';
      case 'CalculationError':
        return '🧮';
      default:
        return '❌';
    }
  };

  const getErrorTitle = (errorType?: string) => {
    switch (errorType) {
      case 'RepositoryNotFound':
        return 'Repository Not Found';
      case 'WebsiteNotFound':
        return 'Website Not Found';
      case 'AccessForbidden':
        return 'Access Forbidden';
      case 'RateLimitExceeded':
        return 'Rate Limit Exceeded';
      case 'TimeoutError':
        return 'Request Timed Out';
      case 'NetworkError':
        return 'Network Error';
      case 'NoComponentsDetected':
        return 'No Components Detected';
      case 'ValidationError':
        return 'Invalid Input';
      case 'CalculationError':
        return 'Calculation Error';
      default:
        return 'Error Occurred';
    }
  };

  const baseClasses = variant === 'page' 
    ? "min-h-screen bg-gray-900 text-terminal-green font-mono flex items-center justify-center"
    : "bg-gray-800 border border-terminal-red rounded-lg p-6";

  const contentClasses = variant === 'page'
    ? "max-w-2xl mx-auto p-8"
    : "";

  const cardClasses = variant === 'page'
    ? "bg-gray-800 border border-terminal-red rounded-lg p-8 text-center"
    : "text-center";

  return (
    <div className={baseClasses}>
      <div className={contentClasses}>
        <div className={cardClasses}>
          <div className="text-4xl mb-4">
            {getErrorIcon(error.error)}
          </div>
          
          <h2 className="text-xl font-bold text-terminal-red mb-3">
            {getErrorTitle(error.error)}
          </h2>
          
          <p className="text-gray-300 mb-6">
            {error.message}
          </p>

          {/* Suggestions */}
          {error.suggestions && error.suggestions.length > 0 && (
            <div className="bg-gray-900 border border-terminal-amber/30 rounded-lg p-4 mb-6 text-left">
              <h3 className="text-terminal-amber font-semibold mb-2 flex items-center">
                💡 Suggestions:
              </h3>
              <ul className="text-sm text-gray-300 space-y-1">
                {error.suggestions.map((suggestion, index) => (
                  <li key={index} className="flex items-start">
                    <span className="text-terminal-amber mr-2">•</span>
                    <span>{suggestion}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Failed Detections (for NoComponentsDetected errors) */}
          {error.failed_detections && error.failed_detections.length > 0 && (
            <div className="bg-gray-900 border border-gray-600 rounded-lg p-4 mb-6 text-left">
              <h3 className="text-gray-400 font-semibold mb-2 flex items-center">
                🔍 Detection Attempts:
              </h3>
              <div className="text-xs text-gray-400 max-h-32 overflow-y-auto">
                {error.failed_detections.slice(0, 10).map((detection, index) => (
                  <div key={index} className="mb-1 font-mono">
                    {detection}
                  </div>
                ))}
                {error.failed_detections.length > 10 && (
                  <div className="text-gray-500 italic">
                    ... and {error.failed_detections.length - 10} more
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Troubleshooting Info (for development) */}
          {process.env.NODE_ENV === 'development' && error.troubleshooting && (
            <div className="bg-gray-900 border border-gray-600 rounded-lg p-4 mb-6 text-left">
              <h3 className="text-gray-400 font-semibold mb-2">Debug Info:</h3>
              <pre className="text-xs text-gray-400 overflow-auto">
                {JSON.stringify(error.troubleshooting, null, 2)}
              </pre>
            </div>
          )}

          {/* Error ID for support */}
          {error.error_id && (
            <div className="text-xs text-gray-500 mb-6">
              Error ID: {error.error_id}
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            {onRetry && (
              <Button onClick={onRetry} variant="primary">
                Try Again
              </Button>
            )}
            {onReset && (
              <Button onClick={onReset} variant="secondary">
                Start Over
              </Button>
            )}
            {variant === 'page' && !onReset && (
              <Button onClick={() => window.location.reload()} variant="secondary">
                Reload Page
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ErrorDisplay;