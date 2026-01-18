import React, { useState } from 'react';
import { AnalysisResponse, AnalysisError } from '../types';
import { StackDebtAPI } from '../services/api';
import InputInterface from '../components/InputInterface/InputInterface';
import ResultsDisplay from '../components/ResultsDisplay/ResultsDisplay';
import { ErrorDisplay } from '../components/ErrorDisplay';

const HomePage: React.FC = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<AnalysisResponse | null>(null);
  const [error, setError] = useState<AnalysisError | null>(null);

  const handleAnalyze = async (url: string) => {
    setIsLoading(true);
    setError(null);
    setResult(null);

    try {
      // Validate and determine URL type
      const validation = StackDebtAPI.validateAndParseURL(url);
      if (!validation.isValid) {
        throw {
          message: validation.error || 'Invalid URL format',
          code: 'VALIDATION_ERROR',
          details: {
            suggestions: [
              'Ensure the URL starts with http:// or https://',
              'For GitHub repositories, use format: owner/repo or https://github.com/owner/repo',
              'For websites, use format: https://example.com'
            ]
          }
        } as AnalysisError;
      }

      // Normalize URL for API
      const normalizedUrl = StackDebtAPI.normalizeURL(url, validation.type!);

      // Make API request
      const analysisResult = await StackDebtAPI.analyzeInfrastructure({
        url: normalizedUrl,
        analysis_type: validation.type!
      });

      setResult(analysisResult);
    } catch (err) {
      const analysisError = err as AnalysisError;
      setError(analysisError);
      
      // Enhanced error logging
      console.group('🚨 Analysis Error');
      console.error('Error details:', analysisError);
      console.error('Original error:', err);
      console.groupEnd();
      
      // Log to error tracking service (if available)
      if ((window as any).gtag) {
        (window as any).gtag('event', 'analysis_error', {
          error_code: analysisError.code,
          error_message: analysisError.message,
          url: url
        });
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleReset = () => {
    setResult(null);
    setError(null);
  };

  const handleRetry = () => {
    setError(null);
    // The user can try again with the same or different URL
  };

  // Show error page if there's an error
  if (error) {
    return (
      <ErrorDisplay
        error={{
          message: error.message,
          error: error.code,
          suggestions: error.details?.suggestions,
          failed_detections: error.details?.failed_detections,
          troubleshooting: error.details?.troubleshooting,
          error_id: error.details?.error_id
        }}
        onRetry={handleRetry}
        onReset={handleReset}
        variant="page"
      />
    );
  }

  return (
    <div>
      {result ? (
        <ResultsDisplay result={result} onReset={handleReset} />
      ) : (
        <InputInterface 
          onSubmit={handleAnalyze} 
          isLoading={isLoading} 
          error={undefined}
        />
      )}
    </div>
  );
};

export default HomePage;