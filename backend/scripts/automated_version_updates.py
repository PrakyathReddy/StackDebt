#!/usr/bin/env python3
"""
Automated version update scripts for StackDebt Encyclopedia database.

This script provides automated updating of software version data from various
package registries, with scheduling and monitoring capabilities.
"""

import asyncio
import logging
import os
import json
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional
from pathlib import Path
import argparse

# Add the app directory to the path so we can import our modules
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.admin import AdminService, RegistryUpdateRequest
from app.models import ComponentCategory

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('automated_updates.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class AutomatedUpdateScheduler:
    """
    Scheduler for automated version updates from package registries.
    
    Manages periodic updates of software version data with configurable
    schedules and error handling.
    """
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize the automated update scheduler.
        
        Args:
            config_file: Path to configuration file (optional)
        """
        self.admin_service = AdminService()
        self.config = self._load_config(config_file)
        self.update_history = []
        
    def _load_config(self, config_file: Optional[str]) -> Dict[str, Any]:
        """Load configuration from file or use defaults."""
        default_config = {
            "update_schedules": [
                {
                    "software_name": "Node.js",
                    "registry_type": "npm",
                    "package_name": "node",
                    "frequency_hours": 24,
                    "max_versions": 10,
                    "include_prereleases": False,
                    "category": "programming_language"
                },
                {
                    "software_name": "Python",
                    "registry_type": "pypi",
                    "package_name": "python",
                    "frequency_hours": 24,
                    "max_versions": 10,
                    "include_prereleases": False,
                    "category": "programming_language"
                },
                {
                    "software_name": "React",
                    "registry_type": "npm",
                    "package_name": "react",
                    "frequency_hours": 12,
                    "max_versions": 15,
                    "include_prereleases": False,
                    "category": "framework"
                },
                {
                    "software_name": "Vue.js",
                    "registry_type": "npm",
                    "package_name": "vue",
                    "frequency_hours": 12,
                    "max_versions": 15,
                    "include_prereleases": False,
                    "category": "framework"
                },
                {
                    "software_name": "Angular",
                    "registry_type": "npm",
                    "package_name": "@angular/core",
                    "frequency_hours": 12,
                    "max_versions": 15,
                    "include_prereleases": False,
                    "category": "framework"
                },
                {
                    "software_name": "Django",
                    "registry_type": "pypi",
                    "package_name": "django",
                    "frequency_hours": 24,
                    "max_versions": 10,
                    "include_prereleases": False,
                    "category": "framework"
                },
                {
                    "software_name": "Flask",
                    "registry_type": "pypi",
                    "package_name": "flask",
                    "frequency_hours": 24,
                    "max_versions": 10,
                    "include_prereleases": False,
                    "category": "framework"
                },
                {
                    "software_name": "FastAPI",
                    "registry_type": "pypi",
                    "package_name": "fastapi",
                    "frequency_hours": 12,
                    "max_versions": 15,
                    "include_prereleases": False,
                    "category": "framework"
                },
                {
                    "software_name": "Express",
                    "registry_type": "npm",
                    "package_name": "express",
                    "frequency_hours": 24,
                    "max_versions": 10,
                    "include_prereleases": False,
                    "category": "framework"
                },
                {
                    "software_name": "Spring Boot",
                    "registry_type": "maven",
                    "package_name": "spring-boot-starter",
                    "frequency_hours": 24,
                    "max_versions": 10,
                    "include_prereleases": False,
                    "category": "framework"
                }
            ],
            "max_concurrent_updates": 3,
            "retry_attempts": 3,
            "retry_delay_seconds": 60,
            "update_timeout_seconds": 300,
            "log_level": "INFO"
        }
        
        if config_file and os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    file_config = json.load(f)
                    default_config.update(file_config)
                    logger.info(f"Loaded configuration from {config_file}")
            except Exception as e:
                logger.warning(f"Error loading config file {config_file}: {e}")
                logger.info("Using default configuration")
        
        return default_config
    
    async def run_single_update(self, schedule_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run a single update for a software package.
        
        Args:
            schedule_config: Configuration for the update
            
        Returns:
            Dictionary with update results
        """
        software_name = schedule_config['software_name']
        registry_type = schedule_config['registry_type']
        package_name = schedule_config.get('package_name', software_name)
        
        logger.info(f"Starting update for {software_name} from {registry_type}")
        
        try:
            # Create update request
            request = RegistryUpdateRequest(
                software_name=software_name,
                registry_type=registry_type,
                max_versions=schedule_config.get('max_versions', 10),
                include_prereleases=schedule_config.get('include_prereleases', False)
            )
            
            # Perform the update with timeout
            update_task = self.admin_service.update_from_registry(request)
            result = await asyncio.wait_for(
                update_task, 
                timeout=self.config.get('update_timeout_seconds', 300)
            )
            
            if result['success']:
                import_result = result['import_result']
                logger.info(
                    f"Update completed for {software_name}: "
                    f"{import_result['successful']} added, "
                    f"{import_result['skipped']} skipped, "
                    f"{import_result['failed']} failed"
                )
                
                return {
                    'software_name': software_name,
                    'registry_type': registry_type,
                    'success': True,
                    'versions_found': result['versions_found'],
                    'versions_added': import_result['successful'],
                    'versions_skipped': import_result['skipped'],
                    'versions_failed': import_result['failed'],
                    'timestamp': datetime.now().isoformat()
                }
            else:
                logger.warning(f"Update failed for {software_name}: {result['message']}")
                return {
                    'software_name': software_name,
                    'registry_type': registry_type,
                    'success': False,
                    'error': result.get('error', 'unknown'),
                    'message': result['message'],
                    'timestamp': datetime.now().isoformat()
                }
                
        except asyncio.TimeoutError:
            logger.error(f"Update timed out for {software_name}")
            return {
                'software_name': software_name,
                'registry_type': registry_type,
                'success': False,
                'error': 'timeout',
                'message': f'Update timed out after {self.config.get("update_timeout_seconds", 300)} seconds',
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error updating {software_name}: {e}")
            return {
                'software_name': software_name,
                'registry_type': registry_type,
                'success': False,
                'error': 'exception',
                'message': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    async def run_batch_updates(self, schedules: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Run multiple updates concurrently with rate limiting.
        
        Args:
            schedules: List of schedule configurations
            
        Returns:
            Dictionary with batch update results
        """
        logger.info(f"Starting batch update for {len(schedules)} software packages")
        
        # Create semaphore for concurrent update limiting
        semaphore = asyncio.Semaphore(self.config.get('max_concurrent_updates', 3))
        
        async def run_with_semaphore(schedule_config):
            async with semaphore:
                return await self.run_single_update(schedule_config)
        
        # Run updates concurrently
        tasks = [run_with_semaphore(schedule) for schedule in schedules]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        successful_updates = []
        failed_updates = []
        
        for result in results:
            if isinstance(result, Exception):
                failed_updates.append({
                    'error': 'exception',
                    'message': str(result),
                    'timestamp': datetime.now().isoformat()
                })
            elif result.get('success'):
                successful_updates.append(result)
            else:
                failed_updates.append(result)
        
        batch_result = {
            'total_updates': len(schedules),
            'successful_updates': len(successful_updates),
            'failed_updates': len(failed_updates),
            'success_details': successful_updates,
            'failure_details': failed_updates,
            'timestamp': datetime.now().isoformat()
        }
        
        logger.info(
            f"Batch update completed: {len(successful_updates)} successful, "
            f"{len(failed_updates)} failed"
        )
        
        return batch_result
    
    async def run_scheduled_updates(self, force_all: bool = False) -> Dict[str, Any]:
        """
        Run updates based on configured schedules.
        
        Args:
            force_all: If True, run all updates regardless of schedule
            
        Returns:
            Dictionary with scheduled update results
        """
        logger.info("Starting scheduled updates")
        
        schedules_to_run = []
        current_time = datetime.now()
        
        for schedule in self.config['update_schedules']:
            software_name = schedule['software_name']
            frequency_hours = schedule.get('frequency_hours', 24)
            
            # Check if update is due
            if force_all:
                schedules_to_run.append(schedule)
                logger.info(f"Forcing update for {software_name}")
            else:
                # Check last update time (simplified - in production would use database)
                last_update = self._get_last_update_time(software_name)
                if last_update is None or (current_time - last_update).total_seconds() >= frequency_hours * 3600:
                    schedules_to_run.append(schedule)
                    logger.info(f"Update due for {software_name}")
                else:
                    logger.debug(f"Update not due for {software_name}")
        
        if not schedules_to_run:
            logger.info("No updates due at this time")
            return {
                'message': 'No updates due',
                'total_updates': 0,
                'timestamp': datetime.now().isoformat()
            }
        
        # Run the batch updates
        result = await self.run_batch_updates(schedules_to_run)
        
        # Update last run times
        for schedule in schedules_to_run:
            self._update_last_run_time(schedule['software_name'], current_time)
        
        return result
    
    def _get_last_update_time(self, software_name: str) -> Optional[datetime]:
        """Get the last update time for a software package."""
        # In a production system, this would query a database
        # For now, we'll use a simple file-based approach
        history_file = Path('update_history.json')
        
        if not history_file.exists():
            return None
        
        try:
            with open(history_file, 'r') as f:
                history = json.load(f)
                last_update_str = history.get(software_name)
                if last_update_str:
                    return datetime.fromisoformat(last_update_str)
        except Exception as e:
            logger.warning(f"Error reading update history: {e}")
        
        return None
    
    def _update_last_run_time(self, software_name: str, update_time: datetime):
        """Update the last run time for a software package."""
        history_file = Path('update_history.json')
        
        try:
            history = {}
            if history_file.exists():
                with open(history_file, 'r') as f:
                    history = json.load(f)
            
            history[software_name] = update_time.isoformat()
            
            with open(history_file, 'w') as f:
                json.dump(history, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error updating history file: {e}")
    
    async def validate_configuration(self) -> Dict[str, Any]:
        """
        Validate the current configuration.
        
        Returns:
            Dictionary with validation results
        """
        logger.info("Validating configuration")
        
        validation_results = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'schedule_count': len(self.config['update_schedules'])
        }
        
        # Validate each schedule
        for i, schedule in enumerate(self.config['update_schedules']):
            schedule_errors = []
            
            # Required fields
            required_fields = ['software_name', 'registry_type']
            for field in required_fields:
                if field not in schedule:
                    schedule_errors.append(f"Missing required field: {field}")
            
            # Validate registry type
            if 'registry_type' in schedule:
                valid_registries = ['npm', 'pypi', 'maven', 'nuget', 'rubygems', 'crates']
                if schedule['registry_type'] not in valid_registries:
                    schedule_errors.append(f"Invalid registry type: {schedule['registry_type']}")
            
            # Validate frequency
            if 'frequency_hours' in schedule:
                if not isinstance(schedule['frequency_hours'], (int, float)) or schedule['frequency_hours'] <= 0:
                    schedule_errors.append("frequency_hours must be a positive number")
            
            if schedule_errors:
                validation_results['valid'] = False
                validation_results['errors'].append({
                    'schedule_index': i,
                    'software_name': schedule.get('software_name', 'unknown'),
                    'errors': schedule_errors
                })
        
        # Validate global settings
        if self.config.get('max_concurrent_updates', 1) < 1:
            validation_results['valid'] = False
            validation_results['errors'].append("max_concurrent_updates must be at least 1")
        
        if validation_results['valid']:
            logger.info("Configuration validation passed")
        else:
            logger.error(f"Configuration validation failed with {len(validation_results['errors'])} errors")
        
        return validation_results
    
    async def cleanup(self):
        """Cleanup resources."""
        await self.admin_service.close()


async def main():
    """Main entry point for the automated update script."""
    parser = argparse.ArgumentParser(description='Automated version updates for StackDebt Encyclopedia')
    parser.add_argument('--config', '-c', help='Configuration file path')
    parser.add_argument('--force-all', '-f', action='store_true', help='Force all updates regardless of schedule')
    parser.add_argument('--validate-only', '-v', action='store_true', help='Only validate configuration')
    parser.add_argument('--software', '-s', help='Update specific software only')
    parser.add_argument('--registry', '-r', help='Update from specific registry only')
    
    args = parser.parse_args()
    
    scheduler = AutomatedUpdateScheduler(args.config)
    
    try:
        # Validate configuration first
        validation_result = await scheduler.validate_configuration()
        
        if not validation_result['valid']:
            logger.error("Configuration validation failed:")
            for error in validation_result['errors']:
                logger.error(f"  {error}")
            return 1
        
        if args.validate_only:
            logger.info("Configuration validation passed")
            return 0
        
        # Filter schedules if specific software or registry requested
        schedules = scheduler.config['update_schedules']
        
        if args.software:
            schedules = [s for s in schedules if s['software_name'].lower() == args.software.lower()]
            if not schedules:
                logger.error(f"No configuration found for software: {args.software}")
                return 1
        
        if args.registry:
            schedules = [s for s in schedules if s['registry_type'].lower() == args.registry.lower()]
            if not schedules:
                logger.error(f"No configuration found for registry: {args.registry}")
                return 1
        
        # Run updates
        if args.software or args.registry or args.force_all:
            # Run specific updates
            result = await scheduler.run_batch_updates(schedules)
        else:
            # Run scheduled updates
            result = await scheduler.run_scheduled_updates()
        
        # Log results
        logger.info("Update session completed:")
        logger.info(f"  Total updates: {result.get('total_updates', 0)}")
        logger.info(f"  Successful: {result.get('successful_updates', 0)}")
        logger.info(f"  Failed: {result.get('failed_updates', 0)}")
        
        # Return appropriate exit code
        return 0 if result.get('failed_updates', 0) == 0 else 1
        
    except Exception as e:
        logger.error(f"Fatal error in automated updates: {e}")
        return 1
    finally:
        await scheduler.cleanup()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)