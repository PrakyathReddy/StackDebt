# Requirements Document

## Introduction

StackDebt is a web application that performs "Carbon Dating" on software infrastructure by analyzing software version numbers to determine the "Effective Age" of websites or applications. The system calculates the "compound interest" on aging infrastructure, making technical debt visible and shareable through engaging analysis and commentary.

## Glossary

- **StackDebt_System**: The complete web application including frontend, backend, and database
- **Carbon_Dating**: The core algorithm that analyzes software versions to calculate infrastructure age
- **Interrogator**: The frontend React application that handles user input and displays results
- **Archeologist**: The backend FastAPI service that performs infrastructure analysis
- **Encyclopedia**: The PostgreSQL database storing software version release dates
- **Stack_Age**: The calculated effective age of infrastructure in years
- **Component**: Any software element detected in the target (OS, language, library, etc.)
- **Effective_Age**: The weighted age calculation based on component criticality
- **Risk_Level**: Classification of components as Critical, Warning, or OK based on age
- **Weakest_Link_Theory**: Algorithm approach that weights older critical components more heavily

## Requirements

### Requirement 1: User Input Interface

**User Story:** As a developer, I want to analyze infrastructure age by entering a URL or GitHub repository, so that I can understand my technical debt.

#### Acceptance Criteria

1. THE Interrogator SHALL provide a single input field that accepts both website URLs and GitHub repository URLs
2. WHEN a user enters a valid URL, THE StackDebt_System SHALL initiate the carbon dating analysis
3. WHEN a user enters an invalid URL format, THE StackDebt_System SHALL display a clear error message and prevent submission
4. THE Interrogator SHALL display in dark mode with a clean, professional interface
5. WHEN the analysis begins, THE Interrogator SHALL show a terminal-style animation indicating scanning progress

### Requirement 2: Infrastructure Discovery and Analysis

**User Story:** As a system analyst, I want the system to automatically detect software components and their versions, so that I can get comprehensive infrastructure analysis.

#### Acceptance Criteria

1. WHEN analyzing a website URL, THE Archeologist SHALL scrape HTTP headers to detect frontend and publicly visible server software versions only
2. WHEN analyzing a website URL, THE Archeologist SHALL identify web servers, CDNs, frontend frameworks, and other publicly exposed components
3. WHEN analyzing a GitHub repository, THE Archeologist SHALL read package files (package.json, requirements.txt, go.mod, etc.) to identify both frontend and backend dependencies
4. WHEN analyzing a GitHub repository, THE Archeologist SHALL parse Dockerfiles to identify base images, operating systems, and installed software for complete stack analysis
5. WHEN analyzing a GitHub repository, THE Archeologist SHALL detect programming languages, databases, libraries, and infrastructure components from configuration files
6. WHEN component detection fails, THE StackDebt_System SHALL log the failure and continue analysis with available data
7. THE Archeologist SHALL query the Encyclopedia database to retrieve release dates for each identified component version

### Requirement 3: Carbon Dating Algorithm

**User Story:** As a technical lead, I want the system to calculate meaningful infrastructure age using weighted analysis, so that I can prioritize technical debt remediation.

#### Acceptance Criteria

1. THE Carbon_Dating algorithm SHALL assign high weight to critical components (operating systems, programming languages, databases)
2. THE Carbon_Dating algorithm SHALL assign low weight to non-critical components (libraries, minor dependencies)
3. THE Carbon_Dating algorithm SHALL implement Weakest_Link_Theory by emphasizing the age of the oldest critical components
4. WHEN calculating Effective_Age, THE Carbon_Dating algorithm SHALL NOT use simple averaging but SHALL weight toward older critical components
5. THE Carbon_Dating algorithm SHALL output the final Stack_Age in years with one decimal place precision
6. WHEN no components are detected, THE StackDebt_System SHALL return an error indicating insufficient data for analysis

### Requirement 4: Risk Assessment and Classification

**User Story:** As a security engineer, I want components classified by risk level based on their age, so that I can identify security and maintenance concerns.

#### Acceptance Criteria

1. WHEN a component is older than 5 years or past end-of-life, THE StackDebt_System SHALL classify it as Critical Risk
2. WHEN a component is 2-5 years old, THE StackDebt_System SHALL classify it as Warning level
3. WHEN a component is less than 2 years old, THE StackDebt_System SHALL classify it as OK level
4. THE StackDebt_System SHALL display risk levels with appropriate color coding (red for Critical, yellow for Warning, green for OK)
5. THE StackDebt_System SHALL provide contextual information about why each component received its risk classification

### Requirement 5: Results Display and Breakdown

**User Story:** As a developer, I want to see detailed analysis results with component breakdown, so that I can understand what contributes to my infrastructure age.

#### Acceptance Criteria

1. THE Interrogator SHALL display the calculated Stack_Age prominently with contextual commentary
2. THE Interrogator SHALL show a visual timeline breakdown of all detected components with their individual ages
3. THE Interrogator SHALL display each component's name, version, release date, and risk level
4. THE Interrogator SHALL provide engaging "roast" commentary about outdated infrastructure to make results shareable
5. WHEN displaying results, THE Interrogator SHALL organize components by category (OS, Languages, Databases, Libraries)

### Requirement 6: Social Sharing Capability

**User Story:** As a team lead, I want to generate shareable reports of infrastructure analysis, so that I can communicate technical debt to stakeholders.

#### Acceptance Criteria

1. THE Interrogator SHALL provide a "Share Report" feature that generates image cards suitable for social media
2. WHEN generating share cards, THE StackDebt_System SHALL include the Stack_Age, key risk components, and branding
3. THE share cards SHALL be optimized for platforms like Twitter, LinkedIn, and Slack
4. THE Interrogator SHALL allow users to download the generated share cards as image files
5. THE share functionality SHALL work without requiring user authentication or account creation

### Requirement 7: Version Release Date Database

**User Story:** As a system administrator, I want comprehensive and accurate version release date data, so that age calculations are reliable and current.

#### Acceptance Criteria

1. THE Encyclopedia SHALL store release dates for major operating systems (Ubuntu, CentOS, Windows Server, etc.)
2. THE Encyclopedia SHALL store release dates for programming languages (Python, Node.js, Go, Java, etc.)
3. THE Encyclopedia SHALL store release dates for databases (PostgreSQL, MySQL, MongoDB, Redis, etc.)
4. THE Encyclopedia SHALL store release dates for popular libraries and frameworks
5. WHEN a component version is not found in the Encyclopedia, THE StackDebt_System SHALL log the missing data and exclude it from age calculation
6. THE Encyclopedia SHALL support periodic updates to include new software releases

### Requirement 8: API Performance and Reliability

**User Story:** As an end user, I want fast and reliable analysis results, so that I can efficiently assess multiple projects.

#### Acceptance Criteria

1. WHEN analyzing a website, THE Archeologist SHALL complete HTTP header analysis within 10 seconds
2. WHEN analyzing a GitHub repository, THE Archeologist SHALL complete file parsing within 30 seconds for repositories under 100MB
3. THE StackDebt_System SHALL handle concurrent analysis requests from multiple users
4. WHEN external services (GitHub API) are unavailable, THE StackDebt_System SHALL return appropriate error messages
5. THE StackDebt_System SHALL implement rate limiting to prevent abuse while maintaining good user experience

### Requirement 9: Error Handling and User Feedback

**User Story:** As a user, I want clear feedback when analysis fails or encounters issues, so that I can understand what went wrong and how to proceed.

#### Acceptance Criteria

1. WHEN a GitHub repository is private or inaccessible, THE StackDebt_System SHALL display a clear error message explaining access requirements
2. WHEN a website is unreachable or blocks scraping, THE StackDebt_System SHALL inform the user and suggest alternatives
3. WHEN analysis produces no detectable components, THE StackDebt_System SHALL explain possible reasons and suggest troubleshooting steps
4. THE StackDebt_System SHALL log all errors for debugging while displaying user-friendly messages
5. WHEN partial analysis succeeds, THE StackDebt_System SHALL show available results with warnings about incomplete data