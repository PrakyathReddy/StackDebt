/**
 * Property-based tests for InputInterface component URL validation
 * Feature: stackdebt, Property 1: URL Input Validation
 * **Validates: Requirements 1.1, 1.3**
 */

import * as fc from 'fast-check';

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

import { StackDebtAPI } from '../../../services/api';

describe('InputInterface Property Tests', () => {
  describe('Property 1: URL Input Validation', () => {
    /**
     * **Validates: Requirements 1.1, 1.3**
     * 
     * Property: For any string input, the system should accept it as valid if and only if 
     * it matches either a valid website URL format or a valid GitHub repository URL format
     */
    it('should validate URLs according to defined patterns', () => {
      fc.assert(
        fc.property(
          fc.string(),
          (input: string) => {
            const result = StackDebtAPI.validateAndParseURL(input);
            
            // If the result is valid, it must be either 'website' or 'github' type
            if (result.isValid) {
              expect(result.type).toMatch(/^(website|github)$/);
              expect(result.error).toBeUndefined();
            } else {
              // If invalid, there should be an error message
              expect(result.error).toBeDefined();
              expect(result.type).toBeUndefined();
            }
          }
        ),
        { numRuns: 10 }
      );
    });

    /**
     * Property: Valid GitHub repository URLs should always be recognized as 'github' type
     */
    it('should consistently identify valid GitHub URLs', () => {
      const githubUrlGenerator = fc.oneof(
        // Simple owner/repo format
        fc.record({
          owner: fc.stringOf(fc.constantFrom(...'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.'.split('')), { minLength: 1, maxLength: 39 }),
          repo: fc.stringOf(fc.constantFrom(...'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.'.split('')), { minLength: 1, maxLength: 100 })
        }).map(({ owner, repo }) => `${owner}/${repo}`),
        
        // Full GitHub URLs
        fc.record({
          protocol: fc.constantFrom('https://', 'http://'),
          subdomain: fc.constantFrom('', 'www.'),
          owner: fc.stringOf(fc.constantFrom(...'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.'.split('')), { minLength: 1, maxLength: 39 }),
          repo: fc.stringOf(fc.constantFrom(...'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.'.split('')), { minLength: 1, maxLength: 100 }),
          trailing: fc.constantFrom('', '/')
        }).map(({ protocol, subdomain, owner, repo, trailing }) => 
          `${protocol}${subdomain}github.com/${owner}/${repo}${trailing}`
        ),
        
        // GitHub.com without protocol
        fc.record({
          owner: fc.stringOf(fc.constantFrom(...'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.'.split('')), { minLength: 1, maxLength: 39 }),
          repo: fc.stringOf(fc.constantFrom(...'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.'.split('')), { minLength: 1, maxLength: 100 }),
          trailing: fc.constantFrom('', '/')
        }).map(({ owner, repo, trailing }) => 
          `github.com/${owner}/${repo}${trailing}`
        )
      );

      fc.assert(
        fc.property(
          githubUrlGenerator,
          (githubUrl: string) => {
            const result = StackDebtAPI.validateAndParseURL(githubUrl);
            expect(result.isValid).toBe(true);
            expect(result.type).toBe('github');
            expect(result.error).toBeUndefined();
          }
        ),
        { numRuns: 10 }
      );
    });

    /**
     * Property: Valid website URLs should always be recognized as 'website' type
     */
    it('should consistently identify valid website URLs', () => {
      const websiteUrlGenerator = fc.oneof(
        // Full URLs with protocol
        fc.record({
          protocol: fc.constantFrom('https://', 'http://'),
          domain: fc.domain(),
          port: fc.option(fc.integer({ min: 1, max: 65535 }).map(p => `:${p}`), { nil: '' }),
          path: fc.option(fc.webPath(), { nil: '' })
        }).map(({ protocol, domain, port, path }) => `${protocol}${domain}${port}${path}`),
        
        // Domain without protocol
        fc.record({
          domain: fc.domain(),
          port: fc.option(fc.integer({ min: 1, max: 65535 }).map(p => `:${p}`), { nil: '' }),
          path: fc.option(fc.webPath(), { nil: '' })
        }).map(({ domain, port, path }) => `${domain}${port}${path}`)
      );

      fc.assert(
        fc.property(
          websiteUrlGenerator,
          (websiteUrl: string) => {
            // Skip URLs that might be confused with GitHub patterns
            fc.pre(!websiteUrl.includes('github.com'));
            fc.pre(!websiteUrl.match(/^[\w-.]+\/[\w-.]+$/));
            
            const result = StackDebtAPI.validateAndParseURL(websiteUrl);
            expect(result.isValid).toBe(true);
            expect(result.type).toBe('website');
            expect(result.error).toBeUndefined();
          }
        ),
        { numRuns: 100 }
      );
    });

    /**
     * Property: Empty or whitespace-only strings should always be invalid
     */
    it('should reject empty or whitespace-only inputs', () => {
      const whitespaceGenerator = fc.stringOf(fc.constantFrom(' ', '\t', '\n', '\r'), { minLength: 0, maxLength: 10 });

      fc.assert(
        fc.property(
          whitespaceGenerator,
          (whitespaceString: string) => {
            const result = StackDebtAPI.validateAndParseURL(whitespaceString);
            expect(result.isValid).toBe(false);
            expect(result.error).toBeDefined();
            expect(result.type).toBeUndefined();
          }
        ),
        { numRuns: 50 }
      );
    });

    /**
     * Property: Invalid URL formats should always be rejected with error messages
     */
    it('should reject clearly invalid URL formats', () => {
      const invalidUrlGenerator = fc.oneof(
        // Random strings that don't match URL patterns
        fc.stringOf(fc.constantFrom(...'!@#$%^&*()+=[]{}|\\:";\'<>?,./`~'.split('')), { minLength: 1, maxLength: 20 }),
        
        // Unsupported protocols
        fc.record({
          protocol: fc.constantFrom('ftp://', 'file://', 'mailto:', 'tel:'),
          rest: fc.string({ minLength: 1, maxLength: 20 })
        }).map(({ protocol, rest }) => `${protocol}${rest}`),
        
        // Malformed URLs (excluding ones that might accidentally be valid)
        fc.constantFrom(
          'not-a-url',
          'just text',
          '123.456.789.999' // Invalid IP
        )
      );

      fc.assert(
        fc.property(
          invalidUrlGenerator,
          (invalidUrl: string) => {
            const result = StackDebtAPI.validateAndParseURL(invalidUrl);
            expect(result.isValid).toBe(false);
            expect(result.error).toBeDefined();
            expect(result.error).toContain('valid');
            expect(result.type).toBeUndefined();
          }
        ),
        { numRuns: 10 }
      );
    });

    /**
     * Property: URL validation should be consistent - same input should always produce same result
     */
    it('should be deterministic and consistent', () => {
      fc.assert(
        fc.property(
          fc.string(),
          (input: string) => {
            const result1 = StackDebtAPI.validateAndParseURL(input);
            const result2 = StackDebtAPI.validateAndParseURL(input);
            
            expect(result1.isValid).toBe(result2.isValid);
            expect(result1.type).toBe(result2.type);
            expect(result1.error).toBe(result2.error);
          }
        ),
        { numRuns: 10 }
      );
    });

    /**
     * Property: Trimming whitespace should not affect validation result for valid URLs
     */
    it('should handle whitespace consistently', () => {
      const urlWithWhitespaceGenerator = fc.tuple(
        fc.stringOf(fc.constantFrom(' ', '\t'), { minLength: 0, maxLength: 5 }),
        fc.oneof(
          fc.constant('https://example.com'),
          fc.constant('facebook/react'),
          fc.constant('github.com/owner/repo')
        ),
        fc.stringOf(fc.constantFrom(' ', '\t'), { minLength: 0, maxLength: 5 })
      ).map(([prefix, url, suffix]) => `${prefix}${url}${suffix}`);

      fc.assert(
        fc.property(
          urlWithWhitespaceGenerator,
          (urlWithWhitespace: string) => {
            const resultWithWhitespace = StackDebtAPI.validateAndParseURL(urlWithWhitespace);
            const resultTrimmed = StackDebtAPI.validateAndParseURL(urlWithWhitespace.trim());
            
            // Both should have the same validity and type
            expect(resultWithWhitespace.isValid).toBe(resultTrimmed.isValid);
            expect(resultWithWhitespace.type).toBe(resultTrimmed.type);
          }
        ),
        { numRuns: 5 }
      );
    });
  });
});