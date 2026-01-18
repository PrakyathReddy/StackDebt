import React, { useState } from 'react';
import { InputInterfaceProps } from '../../types';
import { StackDebtAPI } from '../../services/api';
import { Button, Input, TerminalAnimation } from '../UI';

const InputInterface: React.FC<InputInterfaceProps> = ({ onSubmit, isLoading, error }) => {
  const [url, setUrl] = useState('');
  const [validationError, setValidationError] = useState<string>('');
  const [urlType, setUrlType] = useState<'website' | 'github' | null>(null);

  const handleUrlChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newUrl = e.target.value;
    setUrl(newUrl);
    setValidationError('');

    if (newUrl.trim()) {
      const validation = StackDebtAPI.validateAndParseURL(newUrl);
      if (!validation.isValid) {
        setValidationError(validation.error || 'Invalid URL format');
        setUrlType(null);
      } else {
        setUrlType(validation.type || null);
      }
    } else {
      setUrlType(null);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!url.trim()) {
      setValidationError('Please enter a URL');
      return;
    }

    const validation = StackDebtAPI.validateAndParseURL(url);
    if (!validation.isValid) {
      setValidationError(validation.error || 'Invalid URL format');
      return;
    }

    try {
      await onSubmit(url.trim());
    } catch (err) {
      // Error handling is done in parent component
    }
  };

  const analysisSteps = [
    'Initializing carbon dating scanner...',
    'Detecting infrastructure components...',
    'Querying version database...',
    'Calculating effective age...',
    'Generating risk assessment...',
    'Preparing results...'
  ];

  return (
    <div className="max-w-2xl mx-auto">
      {/* Hero Section */}
      <div className="text-center mb-12">
        <h1 className="text-5xl font-bold mb-4">
          <span className="text-terminal-green">Stack</span>
          <span className="text-terminal-amber">Debt</span>
        </h1>
        <p className="text-xl text-gray-400 mb-2">
          Carbon Dating for Software Infrastructure
        </p>
        <p className="text-gray-500">
          Discover the true age of your technology stack and identify technical debt
        </p>
      </div>

      {/* Input Form */}
      {!isLoading && (
        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="relative">
            <Input
              type="text"
              value={url}
              onChange={handleUrlChange}
              placeholder="Enter website URL or GitHub repository (e.g., https://example.com or owner/repo)"
              error={validationError || error}
              helperText={
                urlType === 'website' 
                  ? '🌐 Website analysis - will scan HTTP headers and public technologies'
                  : urlType === 'github'
                  ? '📁 GitHub repository analysis - will scan package files and dependencies'
                  : 'Enter a website URL or GitHub repository to analyze'
              }
              className="text-lg py-4"
            />
            
            {/* URL Type Indicator */}
            {urlType && (
              <div className="absolute right-3 top-12 flex items-center">
                <div className={`px-2 py-1 rounded text-xs font-mono ${
                  urlType === 'website' 
                    ? 'bg-blue-900/50 text-blue-300 border border-blue-500/30'
                    : 'bg-purple-900/50 text-purple-300 border border-purple-500/30'
                }`}>
                  {urlType === 'website' ? 'WEBSITE' : 'GITHUB'}
                </div>
              </div>
            )}
          </div>

          <Button
            type="submit"
            size="lg"
            className="w-full"
            disabled={!url.trim() || !!validationError}
          >
            <span className="flex items-center justify-center space-x-2">
              <span>🔍</span>
              <span>Analyze Infrastructure</span>
            </span>
          </Button>
        </form>
      )}

      {/* Loading Animation */}
      {isLoading && (
        <div className="space-y-8">
          <TerminalAnimation 
            steps={analysisSteps}
            speed={1500}
          />
          <div className="text-center">
            <p className="text-gray-400 mb-4">
              This may take a few moments while we analyze your infrastructure...
            </p>
            <div className="flex justify-center">
              <Button
                variant="secondary"
                size="sm"
                onClick={() => window.location.reload()}
              >
                Cancel Analysis
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Examples Section */}
      {!isLoading && (
        <div className="mt-16 text-center">
          <h3 className="text-lg font-semibold text-terminal-green mb-4">
            Try these examples:
          </h3>
          <div className="grid md:grid-cols-2 gap-4">
            <button
              onClick={() => setUrl('https://github.com/facebook/react')}
              className="p-4 bg-gray-800 border border-green-400/30 rounded-lg hover:border-terminal-green transition-colors text-left"
            >
              <div className="font-mono text-terminal-green">facebook/react</div>
              <div className="text-sm text-gray-400 mt-1">Popular GitHub repository</div>
            </button>
            <button
              onClick={() => setUrl('https://stackoverflow.com')}
              className="p-4 bg-gray-800 border border-green-400/30 rounded-lg hover:border-terminal-green transition-colors text-left"
            >
              <div className="font-mono text-terminal-green">stackoverflow.com</div>
              <div className="text-sm text-gray-400 mt-1">Website analysis</div>
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default InputInterface;