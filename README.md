# StackDebt - Carbon Dating for Software Infrastructure

StackDebt is a web application that performs "Carbon Dating" on software infrastructure by analyzing version numbers to calculate the "Effective Age" of technology stacks. The system uses a three-tier architecture to provide engaging technical debt analysis with shareable results.

## Architecture

- **Interrogator** (Frontend): React + TypeScript + Tailwind CSS
- **Archeologist** (Backend): Python FastAPI with async/await
- **Encyclopedia** (Database): PostgreSQL with comprehensive version data

## Features

- 🔍 **Infrastructure Analysis**: Analyze websites via HTTP headers or GitHub repositories via file parsing
- ⚖️ **Weighted Age Calculation**: Uses "Weakest Link Theory" to emphasize critical components
- 🎯 **Risk Assessment**: Classifies components as Critical, Warning, or OK based on age
- 📊 **Visual Results**: Timeline breakdown with engaging "roast" commentary
- 📱 **Social Sharing**: Generate shareable cards for Twitter, LinkedIn, and Slack
- 🌙 **Dark Mode UI**: Terminal-style interface for developer appeal

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Node.js 18+ (for local frontend development)
- Python 3.11+ (for local backend development)

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Node.js 18+ (for local frontend development)
- Python 3.11+ (for local backend development)

### Production Deployment (Recommended)

1. Clone the repository:
```bash
git clone <repository-url>
cd stackdebt
```

2. Configure production environment:
```bash
cp .env.production .env.production
# Edit .env.production with your secure passwords and configuration
```

3. Deploy in production mode:
```bash
make deploy-prod
```

4. Access the application:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

5. Monitor the deployment:
```bash
make monitor-prod
```

### Development Setup

#### Using Docker (Recommended for Development)

1. Copy environment configuration:
```bash
cp .env.example .env
```

2. Start all services:
```bash
make start
```

3. Access the application:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- Database: localhost:5432

## Production Deployment

### Quick Production Setup

1. **Configure Environment**:
```bash
cp .env.production .env.production
# Edit the file with secure passwords and your configuration
```

2. **Deploy**:
```bash
make deploy-prod
```

3. **Monitor**:
```bash
make monitor-prod
```

### Production Configuration

The production deployment includes:

- **Security**: Non-root containers, secure passwords, network isolation
- **Performance**: Nginx reverse proxy, Redis caching, resource limits
- **Monitoring**: Health checks, performance metrics, logging
- **Scalability**: Container orchestration ready, load balancer support

### Production Commands

```bash
# Deploy in production mode
make deploy-prod

# Check health status
make health-prod

# View production logs
make logs-prod

# Monitor performance
make monitor-prod

# Stop production services
make stop-prod

# Restart production services
make restart-prod

# Backup database
make backup-db

# Restore database
make restore-db BACKUP=backup_file.sql
```

### Environment Variables

Key production environment variables in `.env.production`:

```bash
# Database (required)
POSTGRES_PASSWORD=your_secure_database_password

# Redis (required)
REDIS_PASSWORD=your_secure_redis_password

# GitHub API (optional, for enhanced analysis)
GITHUB_TOKEN=your_github_token

# Performance tuning
RATE_LIMIT_REQUESTS=100
CACHE_TTL=3600

# Ports (optional, defaults shown)
HTTP_PORT=80
HTTPS_PORT=443
BACKEND_PORT=8000
FRONTEND_PORT=3000
```

### Health Monitoring

The system provides comprehensive health monitoring:

- **Health Check**: `GET /health` - Detailed system health
- **Readiness**: `GET /ready` - Service readiness for traffic
- **Performance**: `GET /api/performance/stats` - Performance metrics
- **Cache Stats**: `GET /api/cache/stats` - Cache performance
- **External Services**: `GET /api/external-services/status` - External service health

### Production Architecture

```
Internet → Nginx (Port 80/443) → Frontend (Port 3000)
                                ↓
                               Backend (Port 8000) → Database (Port 5432)
                                ↓                    ↓
                               Redis (Port 6379)    Volume Storage
```

## Development

#### Backend Setup

1. Navigate to backend directory:
```bash
cd backend
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Start PostgreSQL (using Docker):
```bash
docker-compose up -d database
```

5. Run database migrations:
```bash
alembic upgrade head
```

6. Start the backend server:
```bash
uvicorn app.main:app --reload
```

#### Frontend Setup

1. Navigate to frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Start the development server:
```bash
npm start
```

## Project Structure

```
stackdebt/
├── backend/                 # Archeologist (FastAPI Backend)
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py         # FastAPI application
│   │   ├── database.py     # Database configuration
│   │   └── models.py       # SQLAlchemy models
│   ├── alembic/            # Database migrations
│   ├── requirements.txt    # Python dependencies
│   └── Dockerfile
├── frontend/               # Interrogator (React Frontend)
│   ├── public/
│   ├── src/
│   │   ├── App.tsx         # Main application component
│   │   ├── index.tsx       # Application entry point
│   │   └── index.css       # Tailwind CSS imports
│   ├── package.json        # Node.js dependencies
│   └── Dockerfile
├── database/               # Encyclopedia (PostgreSQL)
│   └── init/
│       ├── 01_create_schema.sql  # Database schema
│       └── 02_seed_data.sql      # Initial version data
├── docker-compose.yml      # Multi-service orchestration
└── README.md
```

## API Endpoints

### Analysis Endpoints

- `POST /api/analyze` - Analyze website or GitHub repository
- `GET /api/components/{software_name}/versions` - Get software versions
- `POST /api/share/generate` - Generate social media share cards

### Health Endpoints

- `GET /` - Service status
- `GET /health` - Health check

## Database Schema

### version_releases Table

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| software_name | VARCHAR(255) | Software name (e.g., "Python", "nginx") |
| version | VARCHAR(100) | Version string (e.g., "3.11.0", "1.20.2") |
| release_date | DATE | Official release date |
| end_of_life_date | DATE | End of life date (nullable) |
| category | component_category | Software category enum |
| is_lts | BOOLEAN | Long-term support flag |

### Component Categories

- `operating_system` - OS versions (Ubuntu, CentOS, Windows Server)
- `programming_language` - Language runtimes (Python, Node.js, Java)
- `database` - Database systems (PostgreSQL, MySQL, MongoDB)
- `web_server` - Web servers (Apache, nginx)
- `framework` - Application frameworks (React, Django, Express)
- `library` - Software libraries and packages
- `development_tool` - Development and build tools

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes and add tests
4. Run the test suite: `npm test` (frontend) and `pytest` (backend)
5. Commit your changes: `git commit -am 'Add feature'`
6. Push to the branch: `git push origin feature-name`
7. Submit a pull request

## Testing

### Backend Tests
```bash
cd backend
pytest
```

### Frontend Tests
```bash
cd frontend
npm test
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Inspired by the need to make technical debt visible and actionable
- Built with modern web technologies for performance and developer experience
- Designed for sharing and collaboration around infrastructure improvements