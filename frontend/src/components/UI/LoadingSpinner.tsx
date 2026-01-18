import React from 'react';

interface LoadingSpinnerProps {
  message?: string;
  size?: 'sm' | 'md' | 'lg';
}

const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({ 
  message = 'Analyzing infrastructure...', 
  size = 'md' 
}) => {
  const sizeClasses = {
    sm: 'w-4 h-4',
    md: 'w-8 h-8',
    lg: 'w-12 h-12'
  };

  return (
    <div className="flex flex-col items-center justify-center space-y-4">
      <div className={`${sizeClasses[size]} border-2 border-terminal-green border-t-transparent rounded-full animate-spin`}></div>
      {message && (
        <div className="text-center">
          <p className="text-terminal-green animate-pulse">{message}</p>
          <div className="flex items-center justify-center mt-2 space-x-1">
            <span className="w-2 h-2 bg-terminal-green rounded-full animate-bounce"></span>
            <span className="w-2 h-2 bg-terminal-green rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></span>
            <span className="w-2 h-2 bg-terminal-green rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></span>
          </div>
        </div>
      )}
    </div>
  );
};

export default LoadingSpinner;