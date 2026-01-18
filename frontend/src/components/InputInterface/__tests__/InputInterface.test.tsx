/**
 * Unit tests for InputInterface component
 * Tests specific URL formats and validation scenarios
 * **Validates: Requirements 1.1, 1.3**
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';

// Mock axios to avoid ES module issues
jest.mock('axios', () => ({
  create: jest.fn(() => ({
    post: jest.fn(),
    get: jest.fn(),
    interceptors: {
      request: { use: jest.fn() },
      response: { use: jest.fn() }
    }
  }))
}));

import InputInterface from '../InputInterface';
import { StackDebtAPI } from '../../../services/api';

// Mock the API service
jest.mock('../../../services/api');
const mockStackDebtAPI = StackDebtAPI as jest.Mocked<typeof StackDebtAPI>;

// Mock UI components
jest.mock('../../UI', () => ({
  Button: ({ children, onClick, disabled, ...props }: any) => (
    <button onClick={onClick} disabled={disabled} {...props}>
      {children}
    </button>
  ),
  Input: ({ value, onChange, placeholder, error, helperText, ...props }: any) => (
    <div>
      <input
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        {...props}
      />
      {error && <div data-testid="error-message">{error}</div>}
      {helperText && <div data-testid="helper-text">{helperText}</div>}
    </div>
  ),
  TerminalAnimation: ({ steps }: any) => (
    <div data-testid="terminal-animation">
      {steps.map((step: string, index: number) => (
        <div key={index}>{step}</div>
      ))}
    </div>
  )
}));

describe('InputInterface Component', () => {
  const mockOnSubmit = jest.fn();
  
  beforeEach(() => {
    jest.clearAllMocks();
    
    // Mock the validation function with actual validation logic
    mockStackDebtAPI.validateAndParseURL.mockImplementation((url: string) => {
      if (!url || url.trim().length === 0) {
        return { isValid: false, error: 'URL cannot be empty' };
      }

      const trimmedUrl = url.trim();

      // GitHub repository URL patterns (exact match from actual implementation)
      const githubPatterns = [
        /^https?:\/\/github\.com\/[\w-.]+\/[\w-.]+\/?$/,
        /^https?:\/\/www\.github\.com\/[\w-.]+\/[\w-.]+\/?$/,
        /^github\.com\/[\w-.]+\/[\w-.]+\/?$/,
        /^[\w-.]+\/[\w-.]+$/ // Simple owner/repo format
      ];

      // Check if it's a GitHub URL
      for (const pattern of githubPatterns) {
        if (pattern.test(trimmedUrl)) {
          return { isValid: true, type: 'github' as const };
        }
      }

      // Website URL patterns (exact match from actual implementation)
      const websitePatterns = [
        /^https?:\/\/[\w-.]+(:\d+)?(\/.*)?$/,
        /^[\w-.]+\.[a-zA-Z]{2,}(:\d+)?(\/.*)?$/ // Domain without protocol
      ];

      // Check if it's a website URL
      for (const pattern of websitePatterns) {
        if (pattern.test(trimmedUrl)) {
          return { isValid: true, type: 'website' as const };
        }
      }

      return { 
        isValid: false, 
        error: 'Please enter a valid website URL (e.g., https://example.com) or GitHub repository (e.g., owner/repo)' 
      };
    });
  });

  const renderComponent = (props = {}) => {
    const defaultProps = {
      onSubmit: mockOnSubmit,
      isLoading: false,
      error: undefined
    };
    return render(<InputInterface {...defaultProps} {...props} />);
  };

  describe('URL Validation Edge Cases', () => {
    it('should validate common GitHub repository formats', async () => {
      const user = userEvent.setup();
      renderComponent();
      
      const input = screen.getByPlaceholderText(/Enter website URL or GitHub repository/);
      
      const githubUrls = [
        'facebook/react',
        'microsoft/vscode',
        'owner-name/repo-name',
        'user.name/repo.name',
        'https://github.com/facebook/react',
        'http://github.com/microsoft/vscode',
        'github.com/owner/repo',
        'https://github.com/owner/repo/',
        'github.com/owner/repo/'
      ];

      for (const url of githubUrls) {
        await user.clear(input);
        await user.type(input, url);
        
        await waitFor(() => {
          expect(screen.getByText('GITHUB')).toBeInTheDocument();
          expect(screen.getByTestId('helper-text')).toHaveTextContent('GitHub repository analysis');
        });
      }
    });

    it('should validate common website URL formats', async () => {
      const user = userEvent.setup();
      renderComponent();
      
      const input = screen.getByPlaceholderText(/Enter website URL or GitHub repository/);
      
      const websiteUrls = [
        'https://example.com',
        'http://example.com',
        'https://www.example.com',
        'https://subdomain.example.com',
        'https://example.com/path',
        'https://example.com:8080',
        'https://example.com:3000/path',
        'example.com',
        'www.example.com',
        'subdomain.example.com',
        'https://stackoverflow.com'
      ];

      for (const url of websiteUrls) {
        await user.clear(input);
        await user.type(input, url);
        
        await waitFor(() => {
          expect(screen.getByText('WEBSITE')).toBeInTheDocument();
          expect(screen.getByTestId('helper-text')).toHaveTextContent('Website analysis');
        });
      }
    });

    it('should reject invalid URL formats with appropriate error messages', async () => {
      const user = userEvent.setup();
      renderComponent();
      
      const input = screen.getByPlaceholderText(/Enter website URL or GitHub repository/);
      
      const invalidUrls = [
        { url: 'not-a-url', expectedError: 'Please enter a valid website URL' },
        { url: 'ftp://example.com', expectedError: 'Please enter a valid website URL' },
        { url: 'mailto:test@example.com', expectedError: 'Please enter a valid website URL' },
        { url: 'http://', expectedError: 'Please enter a valid website URL' },
        { url: 'https://', expectedError: 'Please enter a valid website URL' },
        { url: 'just text', expectedError: 'Please enter a valid website URL' },
        { url: 'owner/', expectedError: 'Please enter a valid website URL' },
        { url: '/repo', expectedError: 'Please enter a valid website URL' }
      ];

      for (const { url, expectedError } of invalidUrls) {
        await user.clear(input);
        await user.type(input, url);
        
        await waitFor(() => {
          const errorElement = screen.getByTestId('error-message');
          expect(errorElement).toHaveTextContent(expectedError);
        });
      }
    });

    it('should handle edge cases in GitHub repository names', async () => {
      const user = userEvent.setup();
      renderComponent();
      
      const input = screen.getByPlaceholderText(/Enter website URL or GitHub repository/);
      
      const edgeCaseGithubUrls = [
        'a/b', // Minimal valid repo
        'owner-with-dashes/repo-with-dashes',
        'owner.with.dots/repo.with.dots',
        'owner_with_underscores/repo_with_underscores',
        'Owner123/Repo456', // Mixed case and numbers
        'https://github.com/very-long-owner-name-that-is-still-valid/very-long-repo-name-that-should-work'
      ];

      for (const url of edgeCaseGithubUrls) {
        await user.clear(input);
        await user.type(input, url);
        
        await waitFor(() => {
          expect(screen.getByText('GITHUB')).toBeInTheDocument();
        });
      }
    });

    it('should handle edge cases in website URLs', async () => {
      const user = userEvent.setup();
      renderComponent();
      
      const input = screen.getByPlaceholderText(/Enter website URL or GitHub repository/);
      
      const edgeCaseWebsiteUrls = [
        'a.co', // Short domain
        'very-long-subdomain-name.example.com',
        'example.museum', // Long TLD
        'https://192.168.1.1', // IP address
        'example.localhost',
        'https://example.com/very/long/path/with/many/segments'
      ];

      for (const url of edgeCaseWebsiteUrls) {
        await user.clear(input);
        await user.type(input, url);
        
        await waitFor(() => {
          expect(screen.getByText('WEBSITE')).toBeInTheDocument();
        });
      }
    });

    it('should handle whitespace trimming correctly', async () => {
      const user = userEvent.setup();
      renderComponent();
      
      const input = screen.getByPlaceholderText(/Enter website URL or GitHub repository/);
      
      const urlsWithWhitespace = [
        '  facebook/react  ',
        '\thttps://example.com\t',
        '\n  github.com/owner/repo  \n',
        '   example.com   '
      ];

      for (const url of urlsWithWhitespace) {
        await user.clear(input);
        await user.type(input, url);
        
        await waitFor(() => {
          // Should not show error for valid URLs with whitespace
          expect(screen.queryByTestId('error-message')).not.toBeInTheDocument();
          expect(screen.getByText(/GITHUB|WEBSITE/)).toBeInTheDocument();
        });
      }
    });
  });

  describe('Form Submission', () => {
    it('should prevent submission with empty URL', async () => {
      const user = userEvent.setup();
      renderComponent();
      
      const submitButton = screen.getByRole('button', { name: /Analyze Infrastructure/ });
      
      // The submit button should be disabled for empty URL, preventing submission
      expect(submitButton).toBeDisabled();
      
      await user.click(submitButton);
      
      expect(mockOnSubmit).not.toHaveBeenCalled();
      // No error message is shown because the form submission is prevented by disabled button
      expect(screen.queryByTestId('error-message')).not.toBeInTheDocument();
    });

    it('should prevent submission with invalid URL', async () => {
      const user = userEvent.setup();
      renderComponent();
      
      const input = screen.getByPlaceholderText(/Enter website URL or GitHub repository/);
      const submitButton = screen.getByRole('button', { name: /Analyze Infrastructure/ });
      
      await user.type(input, 'invalid-url');
      await user.click(submitButton);
      
      expect(mockOnSubmit).not.toHaveBeenCalled();
      expect(screen.getByTestId('error-message')).toHaveTextContent('Please enter a valid website URL');
    });

    it('should submit valid URLs', async () => {
      const user = userEvent.setup();
      renderComponent();
      
      const input = screen.getByPlaceholderText(/Enter website URL or GitHub repository/);
      const submitButton = screen.getByRole('button', { name: /Analyze Infrastructure/ });
      
      await user.type(input, 'facebook/react');
      await user.click(submitButton);
      
      expect(mockOnSubmit).toHaveBeenCalledWith('facebook/react');
    });

    it('should trim whitespace before submission', async () => {
      const user = userEvent.setup();
      renderComponent();
      
      const input = screen.getByPlaceholderText(/Enter website URL or GitHub repository/);
      const submitButton = screen.getByRole('button', { name: /Analyze Infrastructure/ });
      
      await user.type(input, '  https://example.com  ');
      await user.click(submitButton);
      
      expect(mockOnSubmit).toHaveBeenCalledWith('https://example.com');
    });
  });

  describe('Loading State', () => {
    it('should show terminal animation when loading', () => {
      renderComponent({ isLoading: true });
      
      expect(screen.getByTestId('terminal-animation')).toBeInTheDocument();
      expect(screen.getByText('Initializing carbon dating scanner...')).toBeInTheDocument();
      expect(screen.getByText(/This may take a few moments/)).toBeInTheDocument();
    });

    it('should hide input form when loading', () => {
      renderComponent({ isLoading: true });
      
      expect(screen.queryByPlaceholderText(/Enter website URL or GitHub repository/)).not.toBeInTheDocument();
      expect(screen.queryByRole('button', { name: /Analyze Infrastructure/ })).not.toBeInTheDocument();
    });

    it('should show cancel button when loading', () => {
      renderComponent({ isLoading: true });
      
      expect(screen.getByRole('button', { name: /Cancel Analysis/ })).toBeInTheDocument();
    });
  });

  describe('Error Display', () => {
    it('should display external error messages', () => {
      const errorMessage = 'Network error occurred';
      renderComponent({ error: errorMessage });
      
      expect(screen.getByTestId('error-message')).toHaveTextContent(errorMessage);
    });

    it('should clear validation errors when input changes', async () => {
      const user = userEvent.setup();
      renderComponent();
      
      const input = screen.getByPlaceholderText(/Enter website URL or GitHub repository/);
      
      // Enter invalid URL
      await user.type(input, 'invalid');
      expect(screen.getByTestId('error-message')).toBeInTheDocument();
      
      // Clear and enter valid URL
      await user.clear(input);
      await user.type(input, 'facebook/react');
      
      expect(screen.queryByTestId('error-message')).not.toBeInTheDocument();
    });
  });

  describe('Example Buttons', () => {
    it('should populate input with example URLs when clicked', async () => {
      const user = userEvent.setup();
      renderComponent();
      
      const input = screen.getByPlaceholderText(/Enter website URL or GitHub repository/);
      
      // Click GitHub example
      const githubExample = screen.getByText('facebook/react');
      await user.click(githubExample);
      
      expect(input).toHaveValue('https://github.com/facebook/react');
      
      // Click website example
      const websiteExample = screen.getByText('stackoverflow.com');
      await user.click(websiteExample);
      
      expect(input).toHaveValue('https://stackoverflow.com');
    });
  });

  describe('URL Type Indicators', () => {
    it('should show correct type indicator for GitHub URLs', async () => {
      const user = userEvent.setup();
      renderComponent();
      
      const input = screen.getByPlaceholderText(/Enter website URL or GitHub repository/);
      
      await user.type(input, 'facebook/react');
      
      await waitFor(() => {
        expect(screen.getByText('GITHUB')).toBeInTheDocument();
        expect(screen.getByText('GITHUB')).toHaveClass('bg-purple-900/50', 'text-purple-300');
      });
    });

    it('should show correct type indicator for website URLs', async () => {
      const user = userEvent.setup();
      renderComponent();
      
      const input = screen.getByPlaceholderText(/Enter website URL or GitHub repository/);
      
      await user.type(input, 'https://example.com');
      
      await waitFor(() => {
        expect(screen.getByText('WEBSITE')).toBeInTheDocument();
        expect(screen.getByText('WEBSITE')).toHaveClass('bg-blue-900/50', 'text-blue-300');
      });
    });

    it('should hide type indicator for invalid URLs', async () => {
      const user = userEvent.setup();
      renderComponent();
      
      const input = screen.getByPlaceholderText(/Enter website URL or GitHub repository/);
      
      await user.type(input, 'invalid-url');
      
      await waitFor(() => {
        expect(screen.queryByText('GITHUB')).not.toBeInTheDocument();
        expect(screen.queryByText('WEBSITE')).not.toBeInTheDocument();
      });
    });
  });

  describe('Accessibility', () => {
    it('should have proper form structure', () => {
      renderComponent();
      
      // Check for form element using querySelector since it might not have role="form"
      const form = document.querySelector('form');
      expect(form).toBeInTheDocument();
      
      const input = screen.getByPlaceholderText(/Enter website URL or GitHub repository/);
      expect(input).toBeInTheDocument();
      
      const submitButton = screen.getByRole('button', { name: /Analyze Infrastructure/ });
      expect(submitButton).toBeInTheDocument();
    });

    it('should disable submit button for invalid input', async () => {
      const user = userEvent.setup();
      renderComponent();
      
      const input = screen.getByPlaceholderText(/Enter website URL or GitHub repository/);
      const submitButton = screen.getByRole('button', { name: /Analyze Infrastructure/ });
      
      await user.type(input, 'invalid-url');
      
      await waitFor(() => {
        expect(submitButton).toBeDisabled();
      });
    });

    it('should enable submit button for valid input', async () => {
      const user = userEvent.setup();
      renderComponent();
      
      const input = screen.getByPlaceholderText(/Enter website URL or GitHub repository/);
      const submitButton = screen.getByRole('button', { name: /Analyze Infrastructure/ });
      
      await user.type(input, 'facebook/react');
      
      await waitFor(() => {
        expect(submitButton).not.toBeDisabled();
      });
    });
  });
});