// Core data types for StackDebt application

export enum ComponentCategory {
  OPERATING_SYSTEM = "operating_system",
  PROGRAMMING_LANGUAGE = "programming_language",
  DATABASE = "database",
  WEB_SERVER = "web_server",
  FRAMEWORK = "framework",
  LIBRARY = "library",
  DEVELOPMENT_TOOL = "development_tool"
}

export enum RiskLevel {
  CRITICAL = "critical",
  WARNING = "warning",
  OK = "ok"
}

export interface Component {
  name: string;
  version: string;
  releaseDate: string;
  endOfLifeDate?: string;
  category: ComponentCategory;
  riskLevel: RiskLevel;
  ageYears: number;
  weight: number;
}

export interface RiskSummary {
  critical: number;
  warning: number;
  ok: number;
}

export interface StackAgeResult {
  effectiveAge: number;
  totalComponents: number;
  riskDistribution: RiskSummary;
  oldestCriticalComponent?: Component;
  roastCommentary: string;
}

export interface AnalysisRequest {
  url: string;
  analysisType: 'website' | 'github';
}

export interface AnalysisResponse {
  stackAgeResult: StackAgeResult;
  components: Component[];
  analysisMetadata: Record<string, any>;
  generatedAt: string;
}

export interface AnalysisError {
  message: string;
  code: string;
  details?: {
    suggestions?: string[];
    failed_detections?: string[];
    troubleshooting?: Record<string, any>;
    error_id?: string;
    status_code?: number;
    [key: string]: any;
  };
}

// Props interfaces for components
export interface InputInterfaceProps {
  onSubmit: (url: string) => Promise<void>;
  isLoading: boolean;
  error?: string;
}

export interface ResultsDisplayProps {
  result: AnalysisResponse;
  onReset: () => void;
}

export interface ShareCardConfig {
  stackAge: number;
  topRisks: Component[];
  branding: BrandingConfig;
  format: 'twitter' | 'linkedin' | 'slack';
}

export interface BrandingConfig {
  logo?: string;
  primaryColor: string;
  secondaryColor: string;
  fontFamily: string;
}