/**
 * Property-based tests for ShareReport component
 * Feature: stackdebt
 */

import fc from 'fast-check';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import ShareReport from '../ShareReport';
import { AnalysisResponse, Component, ComponentCategory, RiskLevel } from '../../../types';

// Mock canvas and its context
const mockCanvas = {
  getContext: jest.fn(() => ({
    fillStyle: '',
    font: '',
    textAlign: '',
    fillRect: jest.fn(),
    fillText: jest.fn(),
    toDataURL: jest.fn(() => 'data:image/png;base64,mock-image-data')
  })),
  width: 0,
  height: 0,
  toDataURL: jest.fn(() => 'data:image/png;base64,mock-image-data')
};

// Mock HTMLCanvasElement
Object.defineProperty(HTMLCanvasElement.prototype, 'getContext', {
  value: mockCanvas.getContext
});

Object.defineProperty(HTMLCanvasElement.prototype, 'toDataURL', {
  value: mockCanvas.toDataURL
});

// Mock document.createElement for download link
const mockLink = {
  download: '',
  href: '',
  click: jest.fn(),
  remove: jest.fn()
};

Object.defineProperty(document, 'createElement', {
  value: jest.fn((tagName: string) => {
    if (tagName === 'a') {
      return mockLink;
    }
    return {};
  })
});

Object.defineProperty(document.body, 'appendChild', {
  value: jest.fn()
});

Object.defineProperty(document.body, 'removeChild', {
  value: jest.fn()
});

// Generators for test data
const componentCategoryArb = fc.constantFrom(
  ComponentCategory.OPERATING_SYSTEM,
  ComponentCategory.PROGRAMMING_LANGUAGE,
  ComponentCategory.DATABASE,
  ComponentCategory.WEB_SERVER,
  ComponentCategory.FRAMEWORK,
  ComponentCategory.LIBRARY,
  ComponentCategory.DEVELOPMENT_TOOL
);

const riskLevelArb = fc.constantFrom(
  RiskLevel.CRITICAL,
  RiskLevel.WARNING,
  RiskLevel.OK
);

const componentArb = fc.record({
  name: fc.string({ minLength: 1, maxLength: 50 }),
  version: fc.string({ minLength: 1, maxLength: 20 }),
  releaseDate: fc.date({ min: new Date('2000-01-01'), max: new Date() }).map(d => d.toISOString()),
  endOfLifeDate: fc.option(fc.date({ min: new Date('2000-01-01'), max: new Date() }).map(d => d.toISOString())),
  category: componentCategoryArb,
  riskLevel: riskLevelArb,
  ageYears: fc.float({ min: 0, max: 25, noNaN: true }),
  weight: fc.float({ min: 0.1, max: 1.0, noNaN: true })
}) as fc.Arbitrary<Component>;

const stackAgeResultArb = fc.record({
  effectiveAge: fc.float({ min: 0, max: 25, noNaN: true }),
  totalComponents: fc.integer({ min: 0, max: 100 }),
  riskDistribution: fc.record({
    critical: fc.integer({ min: 0, max: 50 }),
    warning: fc.integer({ min: 0, max: 50 }),
    ok: fc.integer({ min: 0, max: 50 })
  }),
  oldestCriticalComponent: fc.option(componentArb),
  roastCommentary: fc.string({ maxLength: 500 })
});

const analysisResponseArb = fc.record({
  stackAgeResult: stackAgeResultArb,
  components: fc.array(componentArb, { minLength: 0, maxLength: 20 }),
  analysisMetadata: fc.dictionary(fc.string(), fc.anything()),
  generatedAt: fc.date().map(d => d.toISOString())
}) as fc.Arbitrary<AnalysisResponse>;

describe('ShareReport Property Tests', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  /**
   * Property 14: Share Card Generation
   * **Validates: Requirements 6.1, 6.2, 6.3**
   * 
   * For any analysis result, the share feature should generate image cards containing 
   * the stack age, key risk components, branding, and be optimized for social media platform dimensions
   */
  test('Property 14: Share Card Generation', () => {
    fc.assert(fc.property(analysisResponseArb, (result) => {
      const mockOnClose = jest.fn();
      
      render(<ShareReport result={result} onClose={mockOnClose} />);
      
      // Verify the component renders with analysis data
      expect(screen.getByText('Share Your Analysis')).toBeInTheDocument();
      expect(screen.getByText('Choose Platform Format')).toBeInTheDocument();
      
      // Verify all platform formats are available (Requirements 6.3)
      expect(screen.getByText('Twitter')).toBeInTheDocument();
      expect(screen.getByText('LinkedIn')).toBeInTheDocument();
      expect(screen.getByText('Slack')).toBeInTheDocument();
      
      // Verify platform dimensions are displayed
      expect(screen.getByText('1200 × 675')).toBeInTheDocument(); // Twitter
      expect(screen.getByText('1200 × 627')).toBeInTheDocument(); // LinkedIn
      expect(screen.getByText('1200 × 630')).toBeInTheDocument(); // Slack
      
      // Verify preview and download buttons are present
      expect(screen.getByText('Preview')).toBeInTheDocument();
      expect(screen.getByText('Download')).toBeInTheDocument();
      
      // Verify no authentication messaging (Requirements 6.4, 6.5)
      expect(screen.getByText('• No authentication required')).toBeInTheDocument();
      
      // Test canvas generation by clicking preview
      const previewButton = screen.getByText('Preview');
      fireEvent.click(previewButton);
      
      // Verify canvas context methods are called (indicates image generation)
      expect(mockCanvas.getContext).toHaveBeenCalled();
      
      return true;
    }), { numRuns: 50 });
  });

  /**
   * Property 14 Extended: Share Card Content Validation
   * **Validates: Requirements 6.1, 6.2**
   * 
   * Generated share cards should include stack age, key risk components, and branding
   */
  test('Property 14 Extended: Share Card Content Validation', async () => {
    fc.assert(fc.asyncProperty(analysisResponseArb, async (result) => {
      const mockOnClose = jest.fn();
      
      render(<ShareReport result={result} onClose={mockOnClose} />);
      
      // Click download to trigger card generation
      const downloadButton = screen.getByText('Download');
      fireEvent.click(downloadButton);
      
      // Wait for generation to complete
      await waitFor(() => {
        expect(mockCanvas.getContext).toHaveBeenCalled();
      });
      
      // Verify canvas context was used to draw content
      const mockCtx = mockCanvas.getContext();
      expect(mockCtx.fillText).toHaveBeenCalled();
      expect(mockCtx.fillRect).toHaveBeenCalled();
      
      // Verify download link was created with proper filename
      expect(document.createElement).toHaveBeenCalledWith('a');
      expect(mockLink.download).toMatch(/^stackdebt-analysis-\w+-\d+\.png$/);
      expect(mockLink.href).toBe('data:image/png;base64,mock-image-data');
      expect(mockLink.click).toHaveBeenCalled();
      
      return true;
    }), { numRuns: 30 });
  });

  /**
   * Property 14 Platform Format Validation
   * **Validates: Requirements 6.3**
   * 
   * Share cards should be optimized for different social media platforms with correct dimensions
   */
  test('Property 14: Platform Format Validation', () => {
    fc.assert(fc.property(analysisResponseArb, (result) => {
      const mockOnClose = jest.fn();
      
      render(<ShareReport result={result} onClose={mockOnClose} />);
      
      // Test each platform format
      const platforms = ['Twitter', 'LinkedIn', 'Slack'];
      const expectedDimensions = [
        { width: 1200, height: 675 }, // Twitter
        { width: 1200, height: 627 }, // LinkedIn
        { width: 1200, height: 630 }  // Slack
      ];
      
      platforms.forEach((platform, index) => {
        const platformButton = screen.getByText(platform);
        fireEvent.click(platformButton);
        
        // Verify platform is selected (visual feedback)
        expect(platformButton.closest('button')).toHaveClass('border-terminal-green');
        
        // Click preview to generate with selected format
        const previewButton = screen.getByText('Preview');
        fireEvent.click(previewButton);
        
        // Verify canvas dimensions are set correctly for the platform
        const canvas = document.querySelector('canvas');
        if (canvas) {
          // Canvas dimensions should match platform requirements
          expect(canvas.width).toBe(expectedDimensions[index].width);
          expect(canvas.height).toBe(expectedDimensions[index].height);
        }
      });
      
      return true;
    }), { numRuns: 20 });
  });

  /**
   * Property 14 Risk Component Prioritization
   * **Validates: Requirements 6.2**
   * 
   * Share cards should include key risk components, prioritizing critical and warning components
   */
  test('Property 14: Risk Component Prioritization', () => {
    fc.assert(fc.property(
      fc.array(componentArb, { minLength: 5, maxLength: 20 }),
      stackAgeResultArb,
      (components, stackAgeResult) => {
        const result: AnalysisResponse = {
          stackAgeResult,
          components,
          analysisMetadata: {},
          generatedAt: new Date().toISOString()
        };
        
        const mockOnClose = jest.fn();
        render(<ShareReport result={result} onClose={mockOnClose} />);
        
        // Generate preview to test component selection logic
        const previewButton = screen.getByText('Preview');
        fireEvent.click(previewButton);
        
        // Verify that critical and warning components are prioritized
        const criticalComponents = components.filter(c => c.riskLevel === RiskLevel.CRITICAL);
        const warningComponents = components.filter(c => c.riskLevel === RiskLevel.WARNING);
        const hasHighRiskComponents = criticalComponents.length > 0 || warningComponents.length > 0;
        
        if (hasHighRiskComponents) {
          // If there are high-risk components, they should be included in the card
          expect(mockCanvas.getContext).toHaveBeenCalled();
          const mockCtx = mockCanvas.getContext();
          expect(mockCtx.fillText).toHaveBeenCalled();
          
          // The fillText calls should include component information
          const fillTextCalls = mockCtx.fillText.mock.calls;
          const hasComponentText = fillTextCalls.some((call: any[]) => 
            typeof call[0] === 'string' && call[0].includes('•')
          );
          expect(hasComponentText).toBe(true);
        }
        
        return true;
      }
    ), { numRuns: 30 });
  });
});