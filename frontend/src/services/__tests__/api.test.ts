import { StackDebtAPI } from '../api';

// Mock axios to avoid ES module issues in Jest
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

describe('StackDebtAPI', () => {
  describe('validateAndParseURL', () => {
    it('should validate GitHub repository URLs', () => {
      const testCases = [
        { url: 'facebook/react', expected: { isValid: true, type: 'github' } },
        { url: 'https://github.com/facebook/react', expected: { isValid: true, type: 'github' } },
        { url: 'github.com/facebook/react', expected: { isValid: true, type: 'github' } },
      ];

      testCases.forEach(({ url, expected }) => {
        const result = StackDebtAPI.validateAndParseURL(url);
        expect(result.isValid).toBe(expected.isValid);
        expect(result.type).toBe(expected.type);
      });
    });

    it('should validate website URLs', () => {
      const testCases = [
        { url: 'https://example.com', expected: { isValid: true, type: 'website' } },
        { url: 'http://localhost:3000', expected: { isValid: true, type: 'website' } },
        { url: 'example.com', expected: { isValid: true, type: 'website' } },
      ];

      testCases.forEach(({ url, expected }) => {
        const result = StackDebtAPI.validateAndParseURL(url);
        expect(result.isValid).toBe(expected.isValid);
        expect(result.type).toBe(expected.type);
      });
    });

    it('should reject invalid URLs', () => {
      const invalidUrls = ['', '   ', 'not-a-url', 'ftp://example.com'];

      invalidUrls.forEach(url => {
        const result = StackDebtAPI.validateAndParseURL(url);
        expect(result.isValid).toBe(false);
        expect(result.error).toBeDefined();
      });
    });
  });

  describe('normalizeURL', () => {
    it('should normalize GitHub URLs', () => {
      expect(StackDebtAPI.normalizeURL('facebook/react', 'github'))
        .toBe('https://github.com/facebook/react');
      
      expect(StackDebtAPI.normalizeURL('github.com/facebook/react', 'github'))
        .toBe('https://github.com/facebook/react');
      
      expect(StackDebtAPI.normalizeURL('https://github.com/facebook/react', 'github'))
        .toBe('https://github.com/facebook/react');
    });

    it('should normalize website URLs', () => {
      expect(StackDebtAPI.normalizeURL('example.com', 'website'))
        .toBe('https://example.com');
      
      expect(StackDebtAPI.normalizeURL('https://example.com', 'website'))
        .toBe('https://example.com');
      
      expect(StackDebtAPI.normalizeURL('http://example.com', 'website'))
        .toBe('http://example.com');
    });
  });
});