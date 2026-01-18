import React, { useState } from 'react';
import { Button } from '../UI';

export interface PartialSuccessWarningProps {
  metadata: Record<string, any> & {
    components_detected?: number;
    components_failed?: number;
    partial_success?: boolean;
    warning_level?: 'low' | 'medium' | 'high';
    failed_detection_summary?: string[];
    success_rate?: number;
  };
  onDismiss?: () => void;
}

const PartialSuccessWarning: React.FC<PartialSuccessWarningProps> = ({ 
  metadata, 
  onDismiss 
}) => {
  const [isExpanded, setIsExpanded] = useState(false);
  
  if (!metadata.partial_success || !metadata.components_failed) {
    return null;
  }

  const warningLevel = metadata.warning_level || 'medium';
  const successRate = metadata.success_rate || 0;
  const failedCount = metadata.components_failed || 0;
  const detectedCount = metadata.components_detected || 0;

  const getWarningColor = () => {
    switch (warningLevel) {
      case 'high':
        return 'border-red-500/50 bg-red-900/20';
      case 'medium':
        return 'border-yellow-500/50 bg-yellow-900/20';
      case 'low':
        return 'border-blue-500/50 bg-blue-900/20';
      default:
        return 'border-yellow-500/50 bg-yellow-900/20';
    }
  };

  const getWarningIcon = () => {
    switch (warningLevel) {
      case 'high':
        return '⚠️';
      case 'medium':
        return '⚡';
      case 'low':
        return 'ℹ️';
      default:
        return '⚡';
    }
  };

  const getWarningTitle = () => {
    switch (warningLevel) {
      case 'high':
        return 'Incomplete Analysis';
      case 'medium':
        return 'Partial Results';
      case 'low':
        return 'Minor Detection Issues';
      default:
        return 'Partial Results';
    }
  };

  const getWarningMessage = () => {
    const percentage = Math.round(successRate * 100);
    
    if (warningLevel === 'high') {
      return `Analysis completed with significant limitations. Only ${detectedCount} components were successfully analyzed, while ${failedCount} components couldn't be processed. Results may not reflect the complete technology stack.`;
    } else if (warningLevel === 'medium') {
      return `Analysis completed with ${percentage}% success rate. ${detectedCount} components were analyzed successfully, but ${failedCount} components couldn't be processed.`;
    } else {
      return `Analysis mostly successful (${percentage}% complete). ${failedCount} minor components couldn't be analyzed, but the main technology stack is represented.`;
    }
  };

  return (
    <div className={`border rounded-lg p-4 mb-6 ${getWarningColor()}`}>
      <div className="flex items-start justify-between">
        <div className="flex items-start space-x-3 flex-1">
          <div className="text-2xl">
            {getWarningIcon()}
          </div>
          <div className="flex-1">
            <h3 className="font-semibold text-white mb-2">
              {getWarningTitle()}
            </h3>
            <p className="text-gray-300 text-sm mb-3">
              {getWarningMessage()}
            </p>
            
            {/* Success Rate Bar */}
            <div className="mb-3">
              <div className="flex justify-between text-xs text-gray-400 mb-1">
                <span>Analysis Completeness</span>
                <span>{Math.round(successRate * 100)}%</span>
              </div>
              <div className="w-full bg-gray-700 rounded-full h-2">
                <div 
                  className={`h-2 rounded-full ${
                    successRate > 0.8 ? 'bg-green-500' : 
                    successRate > 0.5 ? 'bg-yellow-500' : 'bg-red-500'
                  }`}
                  style={{ width: `${successRate * 100}%` }}
                />
              </div>
            </div>

            {/* Expandable Details */}
            {metadata.failed_detection_summary && metadata.failed_detection_summary.length > 0 && (
              <div>
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => setIsExpanded(!isExpanded)}
                  className="text-xs p-1 h-auto"
                >
                  {isExpanded ? '▼' : '▶'} Show failed detections ({failedCount})
                </Button>
                
                {isExpanded && (
                  <div className="mt-3 bg-gray-800/50 rounded p-3">
                    <div className="text-xs text-gray-400 space-y-1 max-h-32 overflow-y-auto">
                      {metadata.failed_detection_summary.map((failure, index) => (
                        <div key={index} className="font-mono">
                          • {failure}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
        
        {onDismiss && (
          <Button
            variant="secondary"
            size="sm"
            onClick={onDismiss}
            className="text-gray-400 hover:text-white p-1 h-auto ml-2"
          >
            ✕
          </Button>
        )}
      </div>
    </div>
  );
};

export default PartialSuccessWarning;