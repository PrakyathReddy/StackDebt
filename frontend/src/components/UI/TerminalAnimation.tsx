import React, { useState, useEffect } from 'react';

interface TerminalAnimationProps {
  steps: string[];
  onComplete?: () => void;
  speed?: number; // milliseconds between steps
}

const TerminalAnimation: React.FC<TerminalAnimationProps> = ({ 
  steps, 
  onComplete, 
  speed = 1000 
}) => {
  const [currentStep, setCurrentStep] = useState(0);
  const [displayedSteps, setDisplayedSteps] = useState<string[]>([]);

  useEffect(() => {
    if (currentStep < steps.length) {
      const timer = setTimeout(() => {
        setDisplayedSteps(prev => [...prev, steps[currentStep]]);
        setCurrentStep(prev => prev + 1);
      }, speed);

      return () => clearTimeout(timer);
    } else if (onComplete) {
      onComplete();
    }
  }, [currentStep, steps, speed, onComplete]);

  return (
    <div className="bg-gray-800 border border-green-400/30 rounded-lg p-4 font-mono text-sm">
      <div className="flex items-center mb-2 text-gray-400">
        <div className="flex space-x-1 mr-3">
          <div className="w-3 h-3 bg-red-500 rounded-full"></div>
          <div className="w-3 h-3 bg-yellow-500 rounded-full"></div>
          <div className="w-3 h-3 bg-green-500 rounded-full"></div>
        </div>
        <span>StackDebt Analyzer Terminal</span>
      </div>
      
      <div className="space-y-1">
        {displayedSteps.map((step, index) => (
          <div key={index} className="flex items-center">
            <span className="text-terminal-amber mr-2">$</span>
            <span className="text-terminal-green">{step}</span>
            {index === displayedSteps.length - 1 && (
              <span className="ml-1 w-2 h-4 bg-terminal-green animate-pulse"></span>
            )}
          </div>
        ))}
        
        {currentStep < steps.length && displayedSteps.length > 0 && (
          <div className="flex items-center">
            <span className="text-terminal-amber mr-2">$</span>
            <span className="w-2 h-4 bg-terminal-green animate-pulse"></span>
          </div>
        )}
      </div>
    </div>
  );
};

export default TerminalAnimation;