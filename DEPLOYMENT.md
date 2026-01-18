# StackDebt Production Deployment Guide

This guide covers deploying StackDebt in production environments with proper security, monitoring, and scalability considerations.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Production Architecture](#production-architecture)
3. [Quick Deployment](#quick-deployment)
4. [Configuration](#configuration)
5. [Security](#security)
6. [Monitoring](#monitoring)
7. [Scaling](#scaling)
8. [Troubleshooting](#troubleshooting)
9. [Maintenance](#maintenance)

## Prerequisites

### System Requirements

- **Operating System**: Linux (Ubuntu 20.04+ recommended)
- **Docker**: 20.10+
- **Docker Compose**: 2.0+
- **Memory**: 4GB RAM minimum, 8GB recommended
- **Storage**: 20GB minimum, 50GB recommended
- **Network**: Ports 80, 443, 3000, 8000 available

### Software Dependencies

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Install monitoring tools (optional)
sudo apt-get update
sudo apt-get install -y jq curl htop
```

## Production Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Load Balancer │    │      Nginx      │    │   Application   │
│   (Optional)    │───▶│  Reverse Proxy  │───▶│    Services     │
│                 │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                       │
                       ┌─────────────────┐            │
                       │     Frontend    │◀───────────┤
                       │   (React App)   │            │
                       └─────────────────┘            │
                                                       │
                       ┌─────────────────┐            │
                       │     Backend     │◀───────────┤
                       │   (FastAPI)     │            │
                       └─────────────────┘            │
                                │                      │
                       ┌─────────────────┐            │
                       │     Database    │◀───────────┤
                       │  (PostgreSQL)   │            │
                       └─────────────────┘            │
                                                       │
                       ┌─────────────────┐            │
                       │      Cache      │◀───────────┘
                       │     (Redis)     │
                       └─────────────────┘
```

### Service Components

- **Nginx**: Reverse proxy, SSL termination, static file serving
- **Frontend**: React application served statically
- **Backend**: FastAPI application with async processing
- **Database**: PostgreSQL with persistent storage
- **Cache**: Redis for analysis result caching
- **Monitoring**: Health checks and performance metrics

## Quick Deployment

### 1. Clone and Configure

```bash
# Clone repository
git clone <repository-url>
cd stackdebt

# Configure production environment
cp .env.production .env.production
```

### 2. Edit Configuration

Edit `.env.production` with your settings:

```bash
# Required: Set secure passwords
POSTGRES_PASSWORD=your_secure_database_password_here
REDIS_PASSWORD=your_secure_redis_password_here

# Optional: GitHub token for enhanced analysis
GITHUB_TOKEN=your_github_personal_access_token

# Optional: Customize ports
HTTP_PORT=80
HTTPS_PORT=443
BACKEND_PORT=8000
FRONTEND_PORT=3000
```

### 3. Deploy

```bash
# Deploy all services
make deploy-prod

# Check deployment status
make health-prod

# Monitor services
make monitor-prod
```

## Configuration

### Environment Variables

#### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `POSTGRES_PASSWORD` | Database password | `SecureDBPass123!` |
| `REDIS_PASSWORD` | Redis password | `SecureRedisPass123!` |

#### Optional Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GITHUB_TOKEN` | - | GitHub API token for enhanced repository analysis |
| `HTTP_PORT` | 80 | HTTP port for Nginx |
| `HTTPS_PORT` | 443 | HTTPS port for Nginx |
| `BACKEND_PORT` | 8000 | Backend service port |
| `FRONTEND_PORT` | 3000 | Frontend service port |
| `RATE_LIMIT_REQUESTS` | 100 | API rate limit per window |
| `RATE_LIMIT_WINDOW` | 3600 | Rate limit window in seconds |
| `CACHE_TTL` | 3600 | Cache TTL in seconds |
| `LOG_LEVEL` | info | Logging level (debug, info, warning, error) |

### Performance Tuning

#### Database Configuration

```bash
# In .env.production
POSTGRES_SHARED_BUFFERS=256MB
POSTGRES_EFFECTIVE_CACHE_SIZE=1GB
POSTGRES_MAINTENANCE_WORK_MEM=64MB
POSTGRES_CHECKPOINT_COMPLETION_TARGET=0.9
POSTGRES_WAL_BUFFERS=16MB
POSTGRES_DEFAULT_STATISTICS_TARGET=100
```

#### Redis Configuration

```bash
# In .env.production
REDIS_MAXMEMORY=256mb
REDIS_MAXMEMORY_POLICY=allkeys-lru
REDIS_SAVE_INTERVAL=900
```

#### Application Configuration

```bash
# In .env.production
BACKEND_WORKERS=4
BACKEND_MAX_CONNECTIONS=100
CACHE_TTL=3600
RATE_LIMIT_REQUESTS=100
```

## Security

### Container Security

- **Non-root users**: All containers run as non-root users
- **Read-only filesystems**: Where possible, containers use read-only filesystems
- **Network isolation**: Services communicate through isolated Docker networks
- **Resource limits**: Memory and CPU limits prevent resource exhaustion

### Network Security

```bash
# Firewall configuration (UFW example)
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw deny 3000/tcp   # Block direct frontend access
sudo ufw deny 8000/tcp   # Block direct backend access
sudo ufw deny 5432/tcp   # Block direct database access
sudo ufw deny 6379/tcp   # Block direct Redis access
sudo ufw enable
```

### SSL/TLS Configuration

For production with SSL, update `nginx/conf.d/stackdebt.conf`:

```nginx
server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
    ssl_prefer_server_ciphers off;
    
    # ... rest of configuration
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}
```

### Secrets Management

For production, consider using Docker secrets or external secret management:

```yaml
# docker-compose.prod.yml
secrets:
  postgres_password:
    external: true
  redis_password:
    external: true

services:
  database:
    secrets:
      - postgres_password
    environment:
      POSTGRES_PASSWORD_FILE: /run/secrets/postgres_password
```

## Monitoring

### Health Checks

The system provides multiple health check endpoints:

```bash
# Overall system health
curl http://localhost:8000/health

# Service readiness
curl http://localhost:8000/ready

# Performance metrics
curl http://localhost:8000/api/performance/stats

# Cache statistics
curl http://localhost:8000/api/cache/stats

# External services status
curl http://localhost:8000/api/external-services/status
```

### Monitoring Commands

```bash
# Real-time monitoring
make monitor-prod

# Check service health
make health-prod

# View logs
make logs-prod

# Container resource usage
docker stats $(docker ps --filter "name=stackdebt" -q)
```

### Log Management

Logs are available through Docker Compose:

```bash
# All services
docker-compose -f docker-compose.prod.yml logs -f

# Specific service
docker-compose -f docker-compose.prod.yml logs -f backend

# With timestamps
docker-compose -f docker-compose.prod.yml logs -f -t

# Last N lines
docker-compose -f docker-compose.prod.yml logs --tail=100 backend
```

### Metrics Collection

For production monitoring, consider integrating with:

- **Prometheus**: Metrics collection
- **Grafana**: Metrics visualization
- **ELK Stack**: Log aggregation and analysis
- **Sentry**: Error tracking

## Scaling

### Horizontal Scaling

Scale individual services:

```bash
# Scale backend instances
docker-compose -f docker-compose.prod.yml up -d --scale backend=3

# Scale with load balancer
docker-compose -f docker-compose.prod.yml up -d --scale backend=3 --scale nginx=2
```

### Database Scaling

For high-load scenarios:

1. **Read Replicas**: Configure PostgreSQL read replicas
2. **Connection Pooling**: Use PgBouncer for connection pooling
3. **Partitioning**: Partition large tables by date or category

### Caching Strategy

1. **Redis Clustering**: For high-availability caching
2. **CDN**: Use CloudFlare or AWS CloudFront for static assets
3. **Application Caching**: Implement application-level caching

### Load Balancing

Example Nginx upstream configuration:

```nginx
upstream backend {
    least_conn;
    server backend-1:8000 weight=1 max_fails=3 fail_timeout=30s;
    server backend-2:8000 weight=1 max_fails=3 fail_timeout=30s;
    server backend-3:8000 weight=1 max_fails=3 fail_timeout=30s;
}
```

## Troubleshooting

### Common Issues

#### Service Won't Start

```bash
# Check container logs
docker-compose -f docker-compose.prod.yml logs service-name

# Check container status
docker-compose -f docker-compose.prod.yml ps

# Check resource usage
docker stats
```

#### Database Connection Issues

```bash
# Test database connectivity
docker-compose -f docker-compose.prod.yml exec database pg_isready -U stackdebt_user

# Check database logs
docker-compose -f docker-compose.prod.yml logs database

# Connect to database
docker-compose -f docker-compose.prod.yml exec database psql -U stackdebt_user -d stackdebt_encyclopedia
```

#### Performance Issues

```bash
# Check performance metrics
curl http://localhost:8000/api/performance/stats

# Monitor resource usage
docker stats

# Check cache hit rate
curl http://localhost:8000/api/cache/stats
```

#### Network Issues

```bash
# Test internal connectivity
docker-compose -f docker-compose.prod.yml exec backend curl http://database:5432

# Check network configuration
docker network ls
docker network inspect stackdebt_stackdebt-network
```

### Debug Mode

Enable debug mode for troubleshooting:

```bash
# In .env.production
DEBUG=true
LOG_LEVEL=debug
```

### Recovery Procedures

#### Database Recovery

```bash
# Backup database
make backup-db

# Restore from backup
make restore-db BACKUP=backup_20231201_120000.sql

# Reset database (destructive)
docker-compose -f docker-compose.prod.yml down -v
docker-compose -f docker-compose.prod.yml up -d database
```

#### Cache Recovery

```bash
# Clear cache
curl -X POST http://localhost:8000/api/cache/clear

# Restart Redis
docker-compose -f docker-compose.prod.yml restart redis
```

## Maintenance

### Regular Maintenance Tasks

#### Daily

- Monitor system health
- Check error logs
- Verify backup completion

#### Weekly

- Update system packages
- Review performance metrics
- Clean up old logs

#### Monthly

- Update Docker images
- Review security settings
- Optimize database

### Backup Strategy

#### Database Backups

```bash
# Automated backup script
#!/bin/bash
BACKUP_DIR="/backups/stackdebt"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

# Create backup
docker-compose -f docker-compose.prod.yml exec -T database pg_dump -U stackdebt_user stackdebt_encyclopedia > $BACKUP_DIR/backup_$DATE.sql

# Compress backup
gzip $BACKUP_DIR/backup_$DATE.sql

# Keep only last 30 days
find $BACKUP_DIR -name "backup_*.sql.gz" -mtime +30 -delete
```

#### Configuration Backups

```bash
# Backup configuration files
tar -czf config_backup_$(date +%Y%m%d).tar.gz \
    .env.production \
    docker-compose.prod.yml \
    nginx/ \
    scripts/
```

### Updates

#### Application Updates

```bash
# Pull latest code
git pull origin main

# Rebuild and deploy
make deploy-prod

# Verify deployment
make health-prod
```

#### Security Updates

```bash
# Update base images
docker-compose -f docker-compose.prod.yml pull

# Rebuild with latest base images
docker-compose -f docker-compose.prod.yml build --no-cache

# Deploy updates
docker-compose -f docker-compose.prod.yml up -d
```

### Performance Optimization

#### Database Optimization

```sql
-- Run monthly
VACUUM ANALYZE;
REINDEX DATABASE stackdebt_encyclopedia;

-- Check slow queries
SELECT query, mean_time, calls 
FROM pg_stat_statements 
ORDER BY mean_time DESC 
LIMIT 10;
```

#### Cache Optimization

```bash
# Monitor cache performance
curl http://localhost:8000/api/cache/stats

# Adjust cache TTL based on usage patterns
# Edit .env.production and restart services
```

## Support

For deployment issues:

1. Check the [troubleshooting section](#troubleshooting)
2. Review logs with `make logs-prod`
3. Check system health with `make health-prod`
4. Consult the main README.md for additional information

For production support, ensure you have:

- System specifications
- Error logs
- Configuration files
- Steps to reproduce the issue