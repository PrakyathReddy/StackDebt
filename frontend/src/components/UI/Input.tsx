import React from 'react';

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  helperText?: string;
}

const Input: React.FC<InputProps> = ({
  label,
  error,
  helperText,
  className = '',
  ...props
}) => {
  const inputClasses = `
    w-full px-4 py-3 bg-gray-800 border rounded-lg font-mono text-terminal-green
    placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-offset-2 
    focus:ring-offset-gray-900 transition-all duration-200
    ${error 
      ? 'border-terminal-red focus:ring-terminal-red' 
      : 'border-green-400/30 focus:border-terminal-green focus:ring-terminal-green'
    }
    ${className}
  `;

  return (
    <div className="space-y-2">
      {label && (
        <label className="block text-sm font-medium text-terminal-green">
          {label}
        </label>
      )}
      
      <input
        className={inputClasses}
        {...props}
      />
      
      {error && (
        <p className="text-sm text-terminal-red flex items-center">
          <span className="mr-1">⚠</span>
          {error}
        </p>
      )}
      
      {helperText && !error && (
        <p className="text-sm text-gray-400">
          {helperText}
        </p>
      )}
    </div>
  );
};

export default Input;