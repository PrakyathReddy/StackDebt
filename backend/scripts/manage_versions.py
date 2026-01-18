#!/usr/bin/env python3
"""
Command-line interface for managing StackDebt Encyclopedia versions.

This script provides a convenient CLI for administrators to manage software
version data, including adding versions, running updates, and viewing statistics.
"""

import asyncio
import argparse
import json
import sys
import os
from datetime import date, datetime
from typing import List, Dict, Any

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.admin import AdminService, VersionAddRequest, BulkVersionImportRequest, RegistryUpdateRequest
from app.models import ComponentCategory
from app.encyclopedia import EncyclopediaRepository


class VersionManager:
    """Command-line interface for version management operations."""
    
    def __init__(self):
        self.admin_service = AdminService()
        self.encyclopedia = EncyclopediaRepository()
    
    async def add_version_interactive(self):
        """Interactive version addition with prompts."""
        print("=== Add New Software Version ===")
        
        try:
            # Get software name
            software_name = input("Software name: ").strip()
            if not software_name:
                print("Error: Software name cannot be empty")
                return False
            
            # Get version
            version = input("Version: ").strip()
            if not version:
                print("Error: Version cannot be empty")
                return False
            
            # Get release date
            while True:
                date_str = input("Release date (YYYY-MM-DD) or 'today': ").strip()
                if date_str.lower() == 'today':
                    release_date = date.today()
                    break
                else:
                    try:
                        release_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                        break
                    except ValueError:
                        print("Invalid date format. Please use YYYY-MM-DD or 'today'")
            
            # Get category
            print("\nAvailable categories:")
            categories = list(ComponentCategory)
            for i, cat in enumerate(categories, 1):
                print(f"  {i}. {cat.value}")
            
            while True:
                try:
                    cat_choice = int(input("Select category (number): "))
                    if 1 <= cat_choice <= len(categories):
                        category = categories[cat_choice - 1]
                        break
                    else:
                        print(f"Please enter a number between 1 and {len(categories)}")
                except ValueError:
                    print("Please enter a valid number")
            
            # Get optional fields
            eol_date = None
            eol_str = input("End of life date (YYYY-MM-DD) or press Enter to skip: ").strip()
            if eol_str:
                try:
                    eol_date = datetime.strptime(eol_str, '%Y-%m-%d').date()
                except ValueError:
                    print("Invalid EOL date format, skipping...")
            
            is_lts = input("Is this an LTS version? (y/N): ").strip().lower() == 'y'
            
            # Create request and add version
            request = VersionAddRequest(
                software_name=software_name,
                version=version,
                release_date=release_date,
                category=category,
                end_of_life_date=eol_date,
                is_lts=is_lts
            )
            
            print(f"\nAdding {software_name} {version}...")
            result = await self.admin_service.add_single_version(request)
            
            if result['success']:
                print(f"✅ Successfully added {software_name} {version}")
                if result.get('validation_warnings'):
                    print("⚠️  Validation warnings:")
                    for warning in result['validation_warnings']:
                        print(f"   - {warning}")
            else:
                print(f"❌ Failed to add version: {result['message']}")
                if result.get('validation_errors'):
                    print("Validation errors:")
                    for error in result['validation_errors']:
                        print(f"   - {error}")
            
            return result['success']
            
        except KeyboardInterrupt:
            print("\nOperation cancelled")
            return False
        except Exception as e:
            print(f"Error: {e}")
            return False
    
    async def add_version_from_args(self, args):
        """Add version from command line arguments."""
        try:
            # Parse category
            category = None
            for cat in ComponentCategory:
                if cat.value == args.category:
                    category = cat
                    break
            
            if not category:
                print(f"Error: Invalid category '{args.category}'")
                print(f"Valid categories: {[cat.value for cat in ComponentCategory]}")
                return False
            
            # Parse dates
            release_date = datetime.strptime(args.release_date, '%Y-%m-%d').date()
            eol_date = None
            if args.eol_date:
                eol_date = datetime.strptime(args.eol_date, '%Y-%m-%d').date()
            
            # Create request
            request = VersionAddRequest(
                software_name=args.software_name,
                version=args.version,
                release_date=release_date,
                category=category,
                end_of_life_date=eol_date,
                is_lts=args.lts
            )
            
            print(f"Adding {args.software_name} {args.version}...")
            result = await self.admin_service.add_single_version(request)
            
            if result['success']:
                print(f"✅ Successfully added {args.software_name} {args.version}")
                if result.get('validation_warnings'):
                    print("⚠️  Validation warnings:")
                    for warning in result['validation_warnings']:
                        print(f"   - {warning}")
            else:
                print(f"❌ Failed to add version: {result['message']}")
                if result.get('validation_errors'):
                    print("Validation errors:")
                    for error in result['validation_errors']:
                        print(f"   - {error}")
            
            return result['success']
            
        except ValueError as e:
            print(f"Error parsing date: {e}")
            return False
        except Exception as e:
            print(f"Error: {e}")
            return False
    
    async def bulk_import_from_file(self, filename: str):
        """Import versions from JSON file."""
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
            
            if 'versions' not in data:
                print("Error: JSON file must contain 'versions' array")
                return False
            
            # Convert to version requests
            version_requests = []
            for item in data['versions']:
                try:
                    # Parse category
                    category = None
                    for cat in ComponentCategory:
                        if cat.value == item['category']:
                            category = cat
                            break
                    
                    if not category:
                        print(f"Warning: Invalid category '{item['category']}' for {item.get('software_name', 'unknown')}")
                        continue
                    
                    # Parse dates
                    release_date = datetime.strptime(item['release_date'], '%Y-%m-%d').date()
                    eol_date = None
                    if item.get('end_of_life_date'):
                        eol_date = datetime.strptime(item['end_of_life_date'], '%Y-%m-%d').date()
                    
                    request = VersionAddRequest(
                        software_name=item['software_name'],
                        version=item['version'],
                        release_date=release_date,
                        category=category,
                        end_of_life_date=eol_date,
                        is_lts=item.get('is_lts', False)
                    )
                    version_requests.append(request)
                    
                except Exception as e:
                    print(f"Warning: Skipping invalid entry {item}: {e}")
            
            if not version_requests:
                print("Error: No valid versions found in file")
                return False
            
            print(f"Importing {len(version_requests)} versions...")
            
            bulk_request = BulkVersionImportRequest(versions=version_requests)
            result = await self.admin_service.bulk_import_versions(bulk_request)
            
            print(f"Import completed:")
            print(f"  ✅ Successful: {result['successful']}")
            print(f"  ⏭️  Skipped: {result['skipped']}")
            print(f"  ❌ Failed: {result['failed']}")
            
            if result['errors']:
                print("\nErrors:")
                for error in result['errors'][:5]:  # Show first 5 errors
                    print(f"  - {error['software_name']} {error['version']}: {error['message']}")
                if len(result['errors']) > 5:
                    print(f"  ... and {len(result['errors']) - 5} more errors")
            
            return result['failed'] == 0
            
        except FileNotFoundError:
            print(f"Error: File '{filename}' not found")
            return False
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON file: {e}")
            return False
        except Exception as e:
            print(f"Error: {e}")
            return False
    
    async def update_from_registry(self, software_name: str, registry_type: str, 
                                 max_versions: int = 10, include_prereleases: bool = False):
        """Update versions from package registry."""
        try:
            request = RegistryUpdateRequest(
                software_name=software_name,
                registry_type=registry_type,
                max_versions=max_versions,
                include_prereleases=include_prereleases
            )
            
            print(f"Updating {software_name} from {registry_type} registry...")
            result = await self.admin_service.update_from_registry(request)
            
            if result['success']:
                import_result = result['import_result']
                print(f"✅ Update completed:")
                print(f"  📦 Versions found: {result['versions_found']}")
                print(f"  ✅ Added: {import_result['successful']}")
                print(f"  ⏭️  Skipped: {import_result['skipped']}")
                print(f"  ❌ Failed: {import_result['failed']}")
                
                if import_result['errors']:
                    print("\nErrors:")
                    for error in import_result['errors'][:3]:
                        print(f"  - {error.get('message', 'Unknown error')}")
            else:
                print(f"❌ Update failed: {result['message']}")
            
            return result['success']
            
        except Exception as e:
            print(f"Error: {e}")
            return False
    
    async def show_statistics(self):
        """Display database statistics."""
        try:
            stats = await self.admin_service.get_update_statistics()
            
            if 'error' in stats:
                print(f"Error getting statistics: {stats['message']}")
                return False
            
            db_stats = stats['database_stats']
            
            print("=== Encyclopedia Database Statistics ===")
            print(f"Total versions: {db_stats.get('total_versions', 'N/A')}")
            print(f"Total software: {db_stats.get('total_software', 'N/A')}")
            print(f"Total categories: {db_stats.get('total_categories', 'N/A')}")
            
            if db_stats.get('oldest_release'):
                print(f"Oldest release: {db_stats['oldest_release']}")
            if db_stats.get('newest_release'):
                print(f"Newest release: {db_stats['newest_release']}")
            
            if db_stats.get('versions_by_category'):
                print("\nVersions by category:")
                for category, count in db_stats['versions_by_category'].items():
                    print(f"  {category}: {count}")
            
            print(f"\nSupported registries: {', '.join(stats['update_capabilities']['supported_registries'])}")
            print(f"Last updated: {stats['last_updated']}")
            
            return True
            
        except Exception as e:
            print(f"Error: {e}")
            return False
    
    async def search_software(self, query: str):
        """Search for software in the database."""
        try:
            results = await self.encyclopedia.search_software(query, limit=20)
            
            if not results:
                print(f"No software found matching '{query}'")
                return True
            
            print(f"=== Search Results for '{query}' ===")
            for result in results:
                print(f"{result['software_name']} ({result['category']})")
                print(f"  Versions: {result['version_count']}")
                if result.get('latest_release'):
                    print(f"  Latest: {result['latest_release']}")
                print()
            
            return True
            
        except Exception as e:
            print(f"Error: {e}")
            return False
    
    async def list_versions(self, software_name: str, limit: int = 10):
        """List versions for a specific software."""
        try:
            versions = await self.encyclopedia.get_software_versions(software_name, limit)
            
            if not versions:
                print(f"No versions found for '{software_name}'")
                return True
            
            print(f"=== Versions for {software_name} ===")
            for version in versions:
                lts_marker = " (LTS)" if version.is_lts else ""
                eol_info = f" [EOL: {version.end_of_life_date}]" if version.end_of_life_date else ""
                print(f"{version.version}{lts_marker} - {version.release_date}{eol_info}")
            
            if len(versions) == limit:
                print(f"\n(Showing first {limit} versions)")
            
            return True
            
        except Exception as e:
            print(f"Error: {e}")
            return False
    
    async def cleanup(self):
        """Cleanup resources."""
        await self.admin_service.close()


async def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description='StackDebt Encyclopedia Version Manager')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Add version command
    add_parser = subparsers.add_parser('add', help='Add a new version')
    add_parser.add_argument('--interactive', '-i', action='store_true', help='Interactive mode')
    add_parser.add_argument('--software-name', '-s', help='Software name')
    add_parser.add_argument('--version', '-v', help='Version string')
    add_parser.add_argument('--release-date', '-d', help='Release date (YYYY-MM-DD)')
    add_parser.add_argument('--category', '-c', help='Component category')
    add_parser.add_argument('--eol-date', help='End of life date (YYYY-MM-DD)')
    add_parser.add_argument('--lts', action='store_true', help='Mark as LTS version')
    
    # Import command
    import_parser = subparsers.add_parser('import', help='Import versions from file')
    import_parser.add_argument('file', help='JSON file containing versions')
    
    # Update command
    update_parser = subparsers.add_parser('update', help='Update from registry')
    update_parser.add_argument('software_name', help='Software name')
    update_parser.add_argument('registry_type', help='Registry type (npm, pypi, etc.)')
    update_parser.add_argument('--max-versions', '-m', type=int, default=10, help='Max versions to fetch')
    update_parser.add_argument('--include-prereleases', '-p', action='store_true', help='Include prereleases')
    
    # Stats command
    subparsers.add_parser('stats', help='Show database statistics')
    
    # Search command
    search_parser = subparsers.add_parser('search', help='Search for software')
    search_parser.add_argument('query', help='Search query')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List versions for software')
    list_parser.add_argument('software_name', help='Software name')
    list_parser.add_argument('--limit', '-l', type=int, default=10, help='Max versions to show')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    manager = VersionManager()
    success = False
    
    try:
        if args.command == 'add':
            if args.interactive:
                success = await manager.add_version_interactive()
            else:
                if not all([args.software_name, args.version, args.release_date, args.category]):
                    print("Error: --software-name, --version, --release-date, and --category are required")
                    return 1
                success = await manager.add_version_from_args(args)
        
        elif args.command == 'import':
            success = await manager.bulk_import_from_file(args.file)
        
        elif args.command == 'update':
            success = await manager.update_from_registry(
                args.software_name, args.registry_type, 
                args.max_versions, args.include_prereleases
            )
        
        elif args.command == 'stats':
            success = await manager.show_statistics()
        
        elif args.command == 'search':
            success = await manager.search_software(args.query)
        
        elif args.command == 'list':
            success = await manager.list_versions(args.software_name, args.limit)
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print("\nOperation cancelled")
        return 1
    except Exception as e:
        print(f"Fatal error: {e}")
        return 1
    finally:
        await manager.cleanup()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)