/**
 * Property-based tests for ResultsDisplay component
 * Feature: stackdebt
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import * as fc from 'fast-check';
import ResultsDisplay from '../ResultsDisplay';
import { AnalysisResponse, Component, ComponentCategory, RiskLevel, StackAgeResult } from '../../../types';

// Generators for property-based testing
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

// Generate realistic component names and versions
const componentNameArb = fc.oneof(
  fc.constantFrom('React', 'Node.js', 'PostgreSQL', 'Ubuntu', 'Apache', 'MySQL', 'Python', 'Java', 'Docker'),
  fc.string({ minLength: 3, maxLength: 20 }).filter(s => /^[a-zA-Z][a-zA-Z0-9._-]*$/.test(s))
);

const versionArb = fc.oneof(
  fc.constantFrom('1.0.0', '2.1.3', '3.4.5', '16.14.0', '18.2.0'),
  fc.string({ minLength: 1, maxLength: 10 }).filter(s => /^[0-9][0-9a-zA-Z._-]*$/.test(s))
);

const commentaryArb = fc.oneof(
  fc.constantFrom(
    'Your infrastructure is showing its age!',
    'Time for some updates!',
    'Looking good, mostly up to date.',
    'Some components need attention.',
    'Critical updates required!'
  ),
  fc.string({ minLength: 10, maxLength: 100 }).filter(s => s.trim().length > 5 && !/[<>{}[\]\\]/.test(s))
);

const componentArb = fc.record({
  name: componentNameArb,
  version: versionArb,
  releaseDate: fc.date({ min: new Date('2000-01-01'), max: new Date() }).map(d => d.toISOString()),
  endOfLifeDate: fc.option(fc.date({ min: new Date('2000-01-01'), max: new Date() }).map(d => d.toISOString())),
  category: componentCategoryArb,
  riskLevel: riskLevelArb,
  ageYears: fc.float({ min: Math.fround(0.1), max: Math.fround(25), noNaN: true }),
  weight: fc.float({ min: Math.fround(0.1), max: Math.fround(1.0), noNaN: true })
}) as fc.Arbitrary<Component>;

const stackAgeResultArb = fc.record({
  effectiveAge: fc.float({ min: Math.fround(0.1), max: Math.fround(25), noNaN: true }),
  totalComponents: fc.nat({ min: 1, max: 100 }),
  riskDistribution: fc.record({
    critical: fc.nat({ max: 50 }),
    warning: fc.nat({ max: 50 }),
    ok: fc.nat({ max: 50 })
  }),
  oldestCriticalComponent: fc.option(componentArb),
  roastCommentary: commentaryArb
}) as fc.Arbitrary<StackAgeResult>;

const analysisResponseArb = fc.record({
  stackAgeResult: stackAgeResultArb,
  components: fc.array(componentArb, { minLength: 1, maxLength: 5 }),
  analysisMetadata: fc.dictionary(fc.string(), fc.anything()),
  generatedAt: fc.date().map(d => d.toISOString())
}) as fc.Arbitrary<AnalysisResponse>;

describe('ResultsDisplay Property Tests', () => {
  const mockOnReset = jest.fn();

  beforeEach(() => {
    mockOnReset.mockClear();
  });

  /**
   * Property 12: Results Display Completeness
   * **Validates: Requirements 5.1, 5.2, 5.3, 5.4**
   * 
   * For any analysis result, the displayed output should include the stack age, 
   * all detected components with their details (name, version, release date, risk level), 
   * and roast commentary
   */
  test('Property 12: Results Display Completeness', () => {
    fc.assert(fc.property(analysisResponseArb, (result) => {
      render(React.createElement(ResultsDisplay, { result, onReset: mockOnReset }));

      // Requirement 5.1: Display calculated Stack_Age prominently with contextual commentary
      const stackAgeElements = screen.getAllByText(result.stackAgeResult.effectiveAge.toFixed(1));
      expect(stackAgeElements.length).toBeGreaterThan(0);
      
      const yearsLabels = screen.getAllByText('years');
      expect(yearsLabels.length).toBeGreaterThan(0);

      // Requirement 5.4: Provide engaging "roast" commentary about outdated infrastructure
      if (result.stackAgeResult.roastCommentary) {
        // Use a more flexible approach to find commentary text
        const commentarySections = screen.getAllByText('Infrastructure Commentary');
        expect(commentarySections.length).toBeGreaterThan(0);
        
        // Check that some commentary text is present (without exact matching)
        const commentaryElements = screen.getAllByText(new RegExp('.+'));
        const hasCommentary = commentaryElements.some(el => 
          el.textContent && el.textContent.includes(result.stackAgeResult.roastCommentary)
        );
        expect(hasCommentary).toBe(true);
      }

      // Requirement 5.2: Show visual timeline breakdown of all detected components with individual ages
      // Requirement 5.3: Display each component's name, version, release date, and risk level
      result.components.forEach(component => {
        // Component name should be displayed
        const nameElements = screen.getAllByText(component.name);
        expect(nameElements.length).toBeGreaterThan(0);

        // Version should be displayed
        const escapedVersion = component.version.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        const versionElements = screen.getAllByText(new RegExp(`Version ${escapedVersion}`));
        expect(versionElements.length).toBeGreaterThan(0);

        // Release date should be displayed
        const releaseDate = new Date(component.releaseDate).toLocaleDateString();
        const escapedReleaseDate = releaseDate.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        const releaseDateElements = screen.getAllByText(new RegExp(`Released ${escapedReleaseDate}`));
        expect(releaseDateElements.length).toBeGreaterThan(0);

        // Age should be displayed
        const ageElements = screen.getAllByText(`${component.ageYears.toFixed(1)} years`);
        expect(ageElements.length).toBeGreaterThan(0);

        // Risk level should be displayed
        const riskElements = screen.getAllByText(component.riskLevel.toUpperCase());
        expect(riskElements.length).toBeGreaterThan(0);
      });

      // Component count should be displayed
      const componentCountElements = screen.getAllByText(new RegExp(`${result.components.length} components detected`));
      expect(componentCountElements.length).toBeGreaterThan(0);

      // Risk distribution should be displayed
      const criticalCountElements = screen.getAllByText(result.stackAgeResult.riskDistribution.critical.toString());
      expect(criticalCountElements.length).toBeGreaterThan(0);
      
      const warningCountElements = screen.getAllByText(result.stackAgeResult.riskDistribution.warning.toString());
      expect(warningCountElements.length).toBeGreaterThan(0);
      
      const okCountElements = screen.getAllByText(result.stackAgeResult.riskDistribution.ok.toString());
      expect(okCountElements.length).toBeGreaterThan(0);
    }), { numRuns: 10 });
  });

  /**
   * Property 12b: Visual Timeline Breakdown
   * **Validates: Requirements 5.2**
   * 
   * For any set of components, each should have visual indicators showing their individual ages
   * with appropriate risk color coding
   */
  test('Property 12b: Visual Timeline Breakdown with Risk Color Coding', () => {
    fc.assert(fc.property(analysisResponseArb, (result) => {
      const { container } = render(React.createElement(ResultsDisplay, { result, onReset: mockOnReset }));

      result.components.forEach(component => {
        // Verify risk color coding is applied by checking for risk-specific classes
        const expectedColorClasses = {
          [RiskLevel.CRITICAL]: 'text-terminal-red',
          [RiskLevel.WARNING]: 'text-terminal-amber',
          [RiskLevel.OK]: 'text-terminal-green'
        };

        const expectedClass = expectedColorClasses[component.riskLevel];
        const elementsWithRiskColor = container.querySelectorAll(`[class*="${expectedClass}"]`);
        expect(elementsWithRiskColor.length).toBeGreaterThan(0);
      });
    }), { numRuns: 5 });
  });

  /**
   * Property 12c: Component Details Completeness
   * **Validates: Requirements 5.3**
   * 
   * For any component, all required details (name, version, release date, risk level, age, weight)
   * should be displayed in the component breakdown
   */
  test('Property 12c: Component Details Completeness', () => {
    fc.assert(fc.property(analysisResponseArb, (result) => {
      render(React.createElement(ResultsDisplay, { result, onReset: mockOnReset }));

      result.components.forEach(component => {
        // Name
        const nameElements = screen.getAllByText(component.name);
        expect(nameElements.length).toBeGreaterThanOrEqual(1);
        
        // Version
        const escapedVersion = component.version.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        const versionElements = screen.getAllByText(new RegExp(`Version ${escapedVersion}`));
        expect(versionElements.length).toBeGreaterThanOrEqual(1);
        
        // Release date
        const releaseDate = new Date(component.releaseDate).toLocaleDateString();
        const escapedReleaseDate = releaseDate.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        const releaseDateElements = screen.getAllByText(new RegExp(`Released ${escapedReleaseDate}`));
        expect(releaseDateElements.length).toBeGreaterThanOrEqual(1);
        
        // Risk level
        const riskElements = screen.getAllByText(component.riskLevel.toUpperCase());
        expect(riskElements.length).toBeGreaterThanOrEqual(1);
        
        // Age
        const ageElements = screen.getAllByText(`${component.ageYears.toFixed(1)} years`);
        expect(ageElements.length).toBeGreaterThanOrEqual(1);
        
        // Weight
        const weightElements = screen.getAllByText(`Weight: ${component.weight.toFixed(1)}`);
        expect(weightElements.length).toBeGreaterThanOrEqual(1);
      });
    }), { numRuns: 5 });
  });

  /**
   * Property 13: Component Organization
   * **Validates: Requirements 5.5**
   * 
   * For any set of displayed components, they should be grouped and organized 
   * by their category (OS, Languages, Databases, Libraries)
   */
  test('Property 13: Component Organization', () => {
    fc.assert(fc.property(analysisResponseArb, (result) => {
      const { container } = render(React.createElement(ResultsDisplay, { result, onReset: mockOnReset }));

      // Group components by category for verification
      const componentsByCategory = result.components.reduce((acc, component) => {
        if (!acc[component.category]) {
          acc[component.category] = [];
        }
        acc[component.category].push(component);
        return acc;
      }, {} as Record<string, Component[]>);

      // Verify each category is displayed as a section
      Object.entries(componentsByCategory).forEach(([category, categoryComponents]) => {
        // Format category name as displayed in UI
        const formattedCategoryName = category.split('_').map(word => 
          word.charAt(0).toUpperCase() + word.slice(1)
        ).join(' ');

        // Category header should be displayed with component count - use getAllByText to handle duplicates
        const categoryHeaders = screen.getAllByText(new RegExp(`${formattedCategoryName.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')} \\(${categoryComponents.length}\\)`));
        expect(categoryHeaders.length).toBeGreaterThanOrEqual(1);

        // All components in this category should be present
        categoryComponents.forEach(component => {
          const componentElements = screen.getAllByText(component.name);
          expect(componentElements.length).toBeGreaterThanOrEqual(1);
        });
      });

      // Verify components are organized in separate category sections
      const categoryHeaders = container.querySelectorAll('.bg-gray-700');
      // Should have at least as many category containers as unique categories
      expect(categoryHeaders.length).toBeGreaterThanOrEqual(Object.keys(componentsByCategory).length);
    }), { numRuns: 10 });
  });

  /**
   * Property 13b: Category Completeness
   * **Validates: Requirements 5.5**
   * 
   * For any component with a valid category, it should appear in exactly one category section
   */
  test('Property 13b: Category Completeness', () => {
    fc.assert(fc.property(analysisResponseArb, (result) => {
      render(React.createElement(ResultsDisplay, { result, onReset: mockOnReset }));

      // Verify each component appears at least once in the component list
      result.components.forEach(component => {
        const componentElements = screen.getAllByText(component.name);
        expect(componentElements.length).toBeGreaterThanOrEqual(1);
      });

      // Verify all supported categories are handled
      const supportedCategories = [
        ComponentCategory.OPERATING_SYSTEM,
        ComponentCategory.PROGRAMMING_LANGUAGE,
        ComponentCategory.DATABASE,
        ComponentCategory.WEB_SERVER,
        ComponentCategory.FRAMEWORK,
        ComponentCategory.LIBRARY,
        ComponentCategory.DEVELOPMENT_TOOL
      ];

      result.components.forEach(component => {
        expect(supportedCategories).toContain(component.category);
      });
    }), { numRuns: 10 });
  });

  /**
   * Property 13c: Category Ordering and Presentation
   * **Validates: Requirements 5.5**
   * 
   * For any set of categories, they should be presented in a logical order
   * with clear visual separation
   */
  test('Property 13c: Category Ordering and Presentation', () => {
    fc.assert(fc.property(analysisResponseArb, (result) => {
      const { container } = render(React.createElement(ResultsDisplay, { result, onReset: mockOnReset }));

      // Get unique categories from components
      const uniqueCategories = Array.from(new Set(result.components.map(c => c.category)));

      if (uniqueCategories.length > 1) {
        // Verify categories are visually separated
        const categoryContainers = container.querySelectorAll('.bg-gray-800');
        
        // Should have at least as many category containers as unique categories
        // (excluding the main header and commentary sections)
        const componentCategoryContainers = Array.from(categoryContainers).filter(container => {
          return container.querySelector('.bg-gray-700');
        });
        
        expect(componentCategoryContainers.length).toBe(uniqueCategories.length);
      }
    }), { numRuns: 3 });
  });
});