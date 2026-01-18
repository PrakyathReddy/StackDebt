# Database Update System

This document describes the database update system for the StackDebt Encyclopedia, which provides comprehensive functionality for managing software version data.

## Overview

The database update system consists of three main components:

1. **Admin Interface** - API endpoints for manual version management
2. **Automated Scripts** - Scheduled updates from package registries
3. **Data Validation** - Comprehensive validation for new version entries

## Components

### 1. Admin Interface (`app/admin.py`)

The admin interface provides API endpoints for managing software versions:

#### Features:
- **Single Version Addition**: Add individual software versions with validation
- **Bulk Import**: Import multiple versions at once
- **Registry Updates**: Automatically fetch versions from package registries
- **Statistics**: View database statistics and system health

#### API Endpoints:
- `POST /api/admin/versions/add` - Add a single version
- `POST /api/admin/versions/bulk-import` - Import multiple versions
- `POST /api/admin/versions/update-from-registry` - Update from package registry
- `GET /api/admin/stats` - Get database statistics
- `GET /api/admin/registries` - List supported registries

#### Supported Package Registries:
- **npm** - Node.js packages
- **PyPI** - Python packages
- **Maven Central** - Java packages
- **NuGet** - .NET packages
- **RubyGems** - Ruby packages
- **Crates.io** - Rust packages

### 2. Automated Scripts (`scripts/automated_version_updates.py`)

The automated update system provides scheduled updates from package registries:

#### Features:
- **Configurable Schedules**: Different update frequencies for different software
- **Concurrent Processing**: Multiple updates running in parallel
- **Error Handling**: Retry logic and graceful failure handling
- **Monitoring**: Comprehensive logging and metrics

#### Configuration:
The system uses `config/update_config.json` for configuration:

```json
{
  "update_schedules": [
    {
      "software_name": "React",
      "registry_type": "npm",
      "package_name": "react",
      "frequency_hours": 12,
      "max_versions": 20,
      "include_prereleases": false,
      "category": "framework",
      "priority": "high"
    }
  ],
  "global_settings": {
    "max_concurrent_updates": 3,
    "retry_attempts": 3,
    "update_timeout_seconds": 300
  }
}
```

#### Usage:
```bash
# Run all scheduled updates
python scripts/automated_version_updates.py

# Force all updates regardless of schedule
python scripts/automated_version_updates.py --force-all

# Update specific software
python scripts/automated_version_updates.py --software React

# Update from specific registry
python scripts/automated_version_updates.py --registry npm

# Validate configuration only
python scripts/automated_version_updates.py --validate-only
```

### 3. Data Validation (`app/version_validator.py`)

The validation system ensures data quality and consistency:

#### Validation Types:
- **Format Validation**: Software names, version strings, dates
- **Business Rules**: Software-specific patterns and constraints
- **Consistency Checks**: Cross-field validation and database consistency
- **Duplicate Detection**: Prevent duplicate entries

#### Validation Levels:
- **ERROR**: Blocks addition to database
- **WARNING**: Allows addition but logs concerns
- **INFO**: Informational messages only

#### Software-Specific Rules:
The validator includes rules for common software:
- Version format patterns (semantic versioning, date-based, etc.)
- Expected release cycles
- Category validation
- Historical consistency checks

### 4. CLI Management Tool (`scripts/manage_versions.py`)

A command-line interface for manual version management:

#### Commands:
```bash
# Interactive version addition
python scripts/manage_versions.py add --interactive

# Add version with parameters
python scripts/manage_versions.py add \
  --software-name "React" \
  --version "18.3.0" \
  --release-date "2024-04-25" \
  --category "framework"

# Import from JSON file
python scripts/manage_versions.py import versions.json

# Update from registry
python scripts/manage_versions.py update React npm --max-versions 15

# Show statistics
python scripts/manage_versions.py stats

# Search software
python scripts/manage_versions.py search "react"

# List versions
python scripts/manage_versions.py list React --limit 10
```

## Data Flow

1. **Manual Addition**: Admin uses API or CLI to add versions
2. **Validation**: All data goes through comprehensive validation
3. **Database Storage**: Valid data is stored in PostgreSQL
4. **Automated Updates**: Scheduled scripts fetch new versions from registries
5. **Monitoring**: System tracks success rates and errors

## Validation Process

```
Input Data
    ↓
Format Validation (names, versions, dates)
    ↓
Business Rules (software-specific patterns)
    ↓
Database Consistency (duplicates, chronology)
    ↓
Cross-field Validation (EOL dates, categories)
    ↓
Result: Valid/Invalid + Issues List
```

## Error Handling

The system provides comprehensive error handling:

- **Validation Errors**: Detailed messages with suggestions
- **Network Errors**: Retry logic with exponential backoff
- **Database Errors**: Transaction rollback and logging
- **Registry Errors**: Graceful degradation and fallback

## Monitoring and Logging

- **Structured Logging**: JSON-formatted logs with context
- **Metrics Collection**: Success rates, timing, error counts
- **Health Checks**: Database connectivity and registry availability
- **Alerting**: Configurable alerts for failures and anomalies

## Security Considerations

- **Input Validation**: All inputs are validated and sanitized
- **SQL Injection Prevention**: Parameterized queries only
- **Rate Limiting**: Registry requests are rate-limited
- **Access Control**: Admin endpoints require appropriate permissions

## Performance Optimization

- **Batch Operations**: Bulk imports for efficiency
- **Concurrent Processing**: Parallel registry updates
- **Database Indexing**: Optimized queries for lookups
- **Caching**: Registry responses cached to reduce API calls

## Configuration

### Environment Variables:
- `DATABASE_URL`: PostgreSQL connection string
- `GITHUB_TOKEN`: Optional GitHub API token for higher rate limits

### Configuration Files:
- `config/update_config.json`: Automated update configuration
- `update_history.json`: Last update timestamps (auto-generated)

## Deployment

### Production Setup:
1. Configure database connection
2. Set up automated update schedule (cron job)
3. Configure monitoring and alerting
4. Set up log rotation and archival

### Example Cron Job:
```bash
# Run automated updates every 6 hours
0 */6 * * * cd /path/to/stackdebt/backend && python scripts/automated_version_updates.py >> /var/log/stackdebt-updates.log 2>&1
```

## API Examples

### Add Single Version:
```bash
curl -X POST http://localhost:8000/api/admin/versions/add \
  -H "Content-Type: application/json" \
  -d '{
    "software_name": "React",
    "version": "18.3.0",
    "release_date": "2024-04-25",
    "category": "framework",
    "is_lts": false
  }'
```

### Update from Registry:
```bash
curl -X POST http://localhost:8000/api/admin/versions/update-from-registry \
  -H "Content-Type: application/json" \
  -d '{
    "software_name": "React",
    "registry_type": "npm",
    "max_versions": 15,
    "include_prereleases": false
  }'
```

### Get Statistics:
```bash
curl http://localhost:8000/api/admin/stats
```

## Troubleshooting

### Common Issues:

1. **Registry Timeouts**: Increase timeout settings in configuration
2. **Validation Failures**: Check validation messages for specific issues
3. **Database Errors**: Verify connection string and permissions
4. **Rate Limiting**: Reduce concurrent updates or add delays

### Debug Mode:
Set `log_level` to `DEBUG` in configuration for detailed logging.

### Health Checks:
Use the `/health` endpoint to verify system status.

## Future Enhancements

- **Web UI**: Browser-based admin interface
- **Webhooks**: Notifications for updates and failures
- **Advanced Analytics**: Trend analysis and reporting
- **API Keys**: Authentication for admin endpoints
- **Backup/Restore**: Database backup and recovery tools

## Requirements Validation

This system validates **Requirements 7.6**: "THE Encyclopedia SHALL support periodic updates to include new software releases" by providing:

✅ **Admin Interface**: Manual addition of new software versions  
✅ **Automated Scripts**: Scheduled updates from package registries  
✅ **Data Validation**: Comprehensive validation for new entries  
✅ **Monitoring**: Health checks and error reporting  
✅ **Scalability**: Concurrent processing and batch operations  

The system ensures that the Encyclopedia database can be continuously updated with new software releases while maintaining data quality and system reliability.