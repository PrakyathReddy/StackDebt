# StackDebt Interrogator (Frontend)

The React frontend application for StackDebt - Carbon Dating for Software Infrastructure.

## Features

- **Dark Mode Terminal Theme**: Professional dark interface with terminal-style aesthetics
- **TypeScript Support**: Full type safety and IntelliSense support
- **Tailwind CSS**: Utility-first CSS framework for rapid UI development
- **React Router**: Client-side routing for single-page application
- **API Client**: Axios-based client for backend communication
- **Error Boundaries**: Graceful error handling and user feedback
- **Responsive Design**: Mobile-first responsive layout
- **Loading Animations**: Terminal-style progress indicators
- **URL Validation**: Smart detection of website URLs vs GitHub repositories

## Project Structure

```
src/
├── components/          # Reusable UI components
│   ├── UI/             # Basic UI components (Button, Input, etc.)
│   ├── Layout/         # Layout components
│   ├── InputInterface/ # URL input and validation
│   ├── ResultsDisplay/ # Analysis results display
│   └── ErrorBoundary/  # Error handling
├── pages/              # Page components
├── services/           # API client and external services
├── types/              # TypeScript type definitions
└── __tests__/          # Test files
```

## Getting Started

### Prerequisites

- Node.js 16+ and npm
- Backend API running on port 8000 (configurable via REACT_APP_API_URL)

### Installation

```bash
npm install
```

### Development

```bash
npm start
```

Runs the app in development mode at [http://localhost:3000](http://localhost:3000).

### Testing

```bash
npm test
```

Runs the test suite with Jest and React Testing Library.

### Building

```bash
npm run build
```

Builds the app for production to the `build` folder.

## Environment Configuration

Copy `.env.example` to `.env` and configure:

```bash
# Backend API URL
REACT_APP_API_URL=http://localhost:8000

# Application Configuration
REACT_APP_NAME=StackDebt
REACT_APP_VERSION=1.0.0

# Feature Flags
REACT_APP_ENABLE_DEBUG=true
REACT_APP_ENABLE_ANALYTICS=false
```

## Component Architecture

### InputInterface
- URL validation and type detection
- Terminal-style loading animations
- Error handling and user feedback

### ResultsDisplay
- Stack age visualization
- Component breakdown by category
- Risk level color coding
- Roast commentary display

### API Client
- Axios-based HTTP client
- Request/response interceptors
- Error transformation
- URL validation and normalization

## Styling

The application uses a dark terminal theme with:

- **Primary Colors**: Terminal green (#00ff00), amber (#ffbf00), red (#ff0000)
- **Background**: Dark gray (#111827, #1f2937)
- **Typography**: Monospace fonts for terminal aesthetic
- **Animations**: Subtle terminal-style effects

## Testing Strategy

- **Unit Tests**: Component logic and API client functions
- **Integration Tests**: Component interactions and data flow
- **Property-Based Tests**: URL validation and data transformation (using fast-check)

## Deployment

The application can be deployed as static files to any web server:

```bash
npm run build
serve -s build
```

Or use the included Dockerfile for containerized deployment.

## Browser Support

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## Contributing

1. Follow the existing code style and patterns
2. Add tests for new functionality
3. Update documentation as needed
4. Ensure all tests pass before submitting

## License

Part of the StackDebt project - see main project LICENSE file.