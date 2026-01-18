import React, { useState } from 'react';
import { ResultsDisplayProps, RiskLevel } from '../../types';
import { Button } from '../UI';
import { ShareReport } from '../ShareReport';
import { PartialSuccessWarning } from '../PartialSuccessWarning';

const ResultsDisplay: React.FC<ResultsDisplayProps> = ({ result, onReset }) => {
  const { stack_age_result, components, analysis_metadata } = result;
  const [showShareModal, setShowShareModal] = useState(false);
  const [showPartialWarning, setShowPartialWarning] = useState(true);

  const getRiskColor = (risk: RiskLevel) => {
    switch (risk) {
      case RiskLevel.CRITICAL:
        return 'text-terminal-red border-terminal-red bg-red-900/20';
      case RiskLevel.WARNING:
        return 'text-terminal-amber border-terminal-amber bg-yellow-900/20';
      case RiskLevel.OK:
        return 'text-terminal-green border-terminal-green bg-green-900/20';
      default:
        return 'text-gray-400 border-gray-400 bg-gray-900/20';
    }
  };

  const getRiskIcon = (risk: RiskLevel) => {
    switch (risk) {
      case RiskLevel.CRITICAL:
        return '🚨';
      case RiskLevel.WARNING:
        return '⚠️';
      case RiskLevel.OK:
        return '✅';
      default:
        return '❓';
    }
  };

  // Group components by category
  const componentsByCategory = components.reduce((acc, component) => {
    if (!acc[component.category]) {
      acc[component.category] = [];
    }
    acc[component.category].push(component);
    return acc;
  }, {} as Record<string, typeof components>);

  const formatCategoryName = (category: string) => {
    return category.split('_').map(word => 
      word.charAt(0).toUpperCase() + word.slice(1)
    ).join(' ');
  };

  return (
    <div className="max-w-6xl mx-auto space-y-8">
      {/* Partial Success Warning */}
      {analysis_metadata.partial_success && showPartialWarning && (
        <PartialSuccessWarning
          metadata={analysis_metadata}
          onDismiss={() => setShowPartialWarning(false)}
        />
      )}

      {/* Header with Stack Age */}
      <div className="text-center">
        <div className="inline-block p-8 bg-gray-800 border border-green-400/30 rounded-lg">
          <h2 className="text-2xl font-bold text-terminal-green mb-2">
            Infrastructure Analysis Complete
          </h2>
          <div className="text-6xl font-mono font-bold mb-4">
            <span className="text-terminal-amber">{stack_age_result.effective_age.toFixed(1)}</span>
            <span className="text-terminal-green text-3xl ml-2">years</span>
          </div>
          <p className="text-gray-400">Effective Stack Age</p>
          
          {/* Analysis metadata summary */}
          <div className="mt-4 text-sm text-gray-500">
            {analysis_metadata.components_detected} components analyzed
            {analysis_metadata.components_failed > 0 && (
              <span> • {analysis_metadata.components_failed} components failed</span>
            )}
            {analysis_metadata.analysis_duration_ms && (
              <span> • {Math.round(analysis_metadata.analysis_duration_ms / 1000)}s analysis time</span>
            )}
          </div>
        </div>
      </div>

      {/* Risk Summary */}
      <div className="grid md:grid-cols-3 gap-4">
        <div className="p-4 bg-red-900/20 border border-terminal-red rounded-lg">
          <div className="flex items-center justify-between">
            <span className="text-terminal-red font-semibold">Critical Risk</span>
            <span className="text-2xl">🚨</span>
          </div>
          <div className="text-2xl font-mono font-bold text-terminal-red">
            {stack_age_result.risk_distribution.critical}
          </div>
        </div>
        
        <div className="p-4 bg-yellow-900/20 border border-terminal-amber rounded-lg">
          <div className="flex items-center justify-between">
            <span className="text-terminal-amber font-semibold">Warning</span>
            <span className="text-2xl">⚠️</span>
          </div>
          <div className="text-2xl font-mono font-bold text-terminal-amber">
            {stack_age_result.risk_distribution.warning}
          </div>
        </div>
        
        <div className="p-4 bg-green-900/20 border border-terminal-green rounded-lg">
          <div className="flex items-center justify-between">
            <span className="text-terminal-green font-semibold">OK</span>
            <span className="text-2xl">✅</span>
          </div>
          <div className="text-2xl font-mono font-bold text-terminal-green">
            {stack_age_result.risk_distribution.ok}
          </div>
        </div>
      </div>

      {/* Roast Commentary */}
      {stack_age_result.roast_commentary && (
        <div className="p-6 bg-gray-800 border border-green-400/30 rounded-lg">
          <h3 className="text-lg font-semibold text-terminal-green mb-3 flex items-center">
            <span className="mr-2">💬</span>
            Infrastructure Commentary
          </h3>
          <p className="text-gray-300 italic text-lg leading-relaxed">
            "{stack_age_result.roast_commentary}"
          </p>
        </div>
      )}

      {/* Components by Category */}
      <div className="space-y-6">
        <h3 className="text-xl font-semibold text-terminal-green">
          Component Breakdown ({components.length} components detected)
        </h3>
        
        {Object.entries(componentsByCategory).map(([category, categoryComponents]) => (
          <div key={category} className="bg-gray-800 border border-green-400/30 rounded-lg overflow-hidden">
            <div className="px-6 py-4 bg-gray-700 border-b border-green-400/30">
              <h4 className="text-lg font-semibold text-terminal-green">
                {formatCategoryName(category)} ({categoryComponents.length})
              </h4>
            </div>
            
            <div className="divide-y divide-green-400/10">
              {categoryComponents.map((component, index) => (
                <div key={index} className="px-6 py-4 hover:bg-gray-700/50 transition-colors">
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <div className="flex items-center space-x-3">
                        <span className="text-lg">{getRiskIcon(component.risk_level)}</span>
                        <div>
                          <h5 className="font-mono font-semibold text-terminal-green">
                            {component.name}
                          </h5>
                          <p className="text-sm text-gray-400">
                            Version {component.version} • Released {new Date(component.release_date).toLocaleDateString()}
                          </p>
                        </div>
                      </div>
                    </div>
                    
                    <div className="flex items-center space-x-4">
                      <div className="text-right">
                        <div className="font-mono font-bold text-lg">
                          {component.age_years.toFixed(1)} years
                        </div>
                        <div className="text-xs text-gray-400">
                          Weight: {component.weight.toFixed(1)}
                        </div>
                      </div>
                      
                      <div className={`px-3 py-1 rounded-full text-xs font-mono font-semibold border ${getRiskColor(component.risk_level)}`}>
                        {component.risk_level.toUpperCase()}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* Actions */}
      <div className="flex justify-center space-x-4">
        <Button onClick={onReset} variant="secondary">
          Analyze Another
        </Button>
        <Button onClick={() => setShowShareModal(true)} variant="primary">
          Share Results
        </Button>
      </div>

      {/* Share Modal */}
      {showShareModal && (
        <ShareReport
          result={result}
          onClose={() => setShowShareModal(false)}
        />
      )}
    </div>
  );
};

export default ResultsDisplay;