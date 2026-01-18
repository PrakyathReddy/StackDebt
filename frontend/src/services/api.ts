// API client for backend communication
import axios, { AxiosResponse } from 'axios';
import { AnalysisRequest, AnalysisResponse, AnalysisError } from '../types';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// Create axios instance with default configuration
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000, // 60 seconds timeout for analysis requests
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for logging
apiClient.interceptors.request.use(
  (config) => {
    console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`);
    return config;
  },
  (error) => {
    console.error('API Request Error:', error);
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => {
    console.log(`API Response: ${response.status} ${response.config.url}`);
    return response;
  },
  (error) => {
    console.error('API Response Error:', error);
    
    // Enhanced error transformation with detailed information
    let analysisError: AnalysisError;
    
    if (error.response) {
      // Server responded with error status
      const responseData = error.response.data;
      
      if (responseData && typeof responseData === 'object' && responseData.detail) {
        // Structured error response from FastAPI
        if (typeof responseData.detail === 'object') {
          analysisError = {
            message: responseData.detail.message || 'An error occurred',
            code: responseData.detail.error || 'UNKNOWN_ERROR',
            details: {
              suggestions: responseData.detail.suggestions || [],
              failed_detections: responseData.detail.failed_detections || [],
              troubleshooting: responseData.detail.troubleshooting || {},
              error_id: responseData.detail.error_id,
              status_code: error.response.status
            }
          };
        } else {
          // Simple string error
          analysisError = {
            message: responseData.detail,
            code: `HTTP_${error.response.status}`,
            details: { status_code: error.response.status }
          };
        }
      } else {
        // Fallback for non-structured responses
        analysisError = {
          message: `HTTP ${error.response.status}: ${error.response.statusText}`,
          code: `HTTP_${error.response.status}`,
          details: { status_code: error.response.status }
        };
      }
    } else if (error.request) {
      // Network error (no response received)
      if (error.code === 'ECONNABORTED' || error.message.includes('timeout')) {
        analysisError = {
          message: 'Request timed out. The analysis is taking longer than expected.',
          code: 'TIMEOUT_ERROR',
          details: {
            suggestions: [
              'The target URL may be slow to respond',
              'Try again in a few moments',
              'Check if the URL is accessible'
            ]
          }
        };
      } else {
        analysisError = {
          message: 'Unable to connect to the StackDebt service. Please check your internet connection.',
          code: 'NETWORK_ERROR',
          details: {
            suggestions: [
              'Check your internet connection',
              'Verify the StackDebt service is available',
              'Try again in a few moments'
            ]
          }
        };
      }
    } else {
      // Something else happened
      analysisError = {
        message: error.message || 'An unexpected error occurred',
        code: 'UNKNOWN_ERROR',
        details: {}
      };
    }
    
    return Promise.reject(analysisError);
  }
);

export class StackDebtAPI {
  /**
   * Analyze infrastructure for a given URL (website or GitHub repository)
   */
  static async analyzeInfrastructure(request: AnalysisRequest): Promise<AnalysisResponse> {
    try {
      const response: AxiosResponse<AnalysisResponse> = await apiClient.post('/api/analyze', request);
      return response.data;
    } catch (error) {
      throw error;
    }
  }

  /**
   * Get available versions for a specific software
   */
  static async getSoftwareVersions(softwareName: string): Promise<any[]> {
    try {
      const response = await apiClient.get(`/api/components/${encodeURIComponent(softwareName)}/versions`);
      return response.data;
    } catch (error) {
      throw error;
    }
  }

  /**
   * Health check endpoint
   */
  static async healthCheck(): Promise<{ status: string; timestamp: string }> {
    try {
      const response = await apiClient.get('/api/health');
      return response.data;
    } catch (error) {
      throw error;
    }
  }

  /**
   * Validate URL format and determine analysis type
   */
  static validateAndParseURL(url: string): { isValid: boolean; type?: 'website' | 'github'; error?: string } {
    if (!url || url.trim().length === 0) {
      return { isValid: false, error: 'URL cannot be empty' };
    }

    const trimmedUrl = url.trim();

    // GitHub repository URL patterns
    const githubPatterns = [
      /^https?:\/\/github\.com\/[\w-.]+\/[\w-.]+\/?$/,
      /^https?:\/\/www\.github\.com\/[\w-.]+\/[\w-.]+\/?$/,
      /^github\.com\/[\w-.]+\/[\w-.]+\/?$/,
      /^[\w-.]+\/[\w-.]+$/ // Simple owner/repo format
    ];

    // Check if it's a GitHub URL
    for (const pattern of githubPatterns) {
      if (pattern.test(trimmedUrl)) {
        return { isValid: true, type: 'github' };
      }
    }

    // Website URL patterns
    const websitePatterns = [
      /^https?:\/\/[\w-.]+(:\d+)?(\/.*)?$/,
      /^[\w-.]+\.[a-zA-Z]{2,}(:\d+)?(\/.*)?$/ // Domain without protocol
    ];

    // Check if it's a website URL
    for (const pattern of websitePatterns) {
      if (pattern.test(trimmedUrl)) {
        return { isValid: true, type: 'website' };
      }
    }

    return { 
      isValid: false, 
      error: 'Please enter a valid website URL (e.g., https://example.com) or GitHub repository (e.g., owner/repo)' 
    };
  }

  /**
   * Normalize URL for API consumption
   */
  static normalizeURL(url: string, type: 'website' | 'github'): string {
    const trimmedUrl = url.trim();

    if (type === 'github') {
      // Normalize GitHub URLs to https://github.com/owner/repo format
      if (trimmedUrl.match(/^[\w-.]+\/[\w-.]+$/)) {
        return `https://github.com/${trimmedUrl}`;
      }
      if (trimmedUrl.startsWith('github.com/')) {
        return `https://${trimmedUrl}`;
      }
      return trimmedUrl;
    }

    if (type === 'website') {
      // Add https:// if no protocol specified
      if (!trimmedUrl.match(/^https?:\/\//)) {
        return `https://${trimmedUrl}`;
      }
      return trimmedUrl;
    }

    return trimmedUrl;
  }
}

export default StackDebtAPI;