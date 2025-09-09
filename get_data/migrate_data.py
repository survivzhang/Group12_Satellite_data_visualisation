#!/usr/bin/env python3
"""
Data Migration Utility for Satellite Data Structure

This utility helps migrate satellite data from legacy directory structures
to the new unified structure: data/{satellite}/{parameter}/{file_type}/

Usage:
    python migrate_data.py --check    # Check current data structure
    python migrate_data.py --migrate  # Migrate data to unified structure
    python migrate_data.py --verify   # Verify migration was successful
"""

import argparse
import shutil
import sys
from pathlib import Path
from typing import List, Dict, Tuple
import json
from datetime import datetime


class DataMigrationTool:
    """Tool for migrating satellite data to unified directory structure"""
    
    def __init__(self):
        self.base_dir = Path("data")
        
        # Legacy directory mappings
        self.legacy_dirs = {
            'himawari': {
                'nc': Path("himawari_test_data/data/himawari_l3c/parts"),
                'png': Path("himawari_test_data/data/himawari_l3c/png"),
                'temp': Path("himawari_test_data/data/himawari_l3c/temp")
            },
            'sentinel3a': {
                'nc': Path("saternal3/data/eumetview_sentinel3/sentinel3a"),
                'png': Path("saternal3/data/eumetview_sentinel3/sentinel3a")
            },
            'sentinel3b': {
                'nc': Path("saternal3/data/eumetview_sentinel3/sentinel3b"),
                'png': Path("saternal3/data/eumetview_sentinel3/sentinel3b")
            }
        }
        
        # Unified directory structure
        self.unified_structure = {
            'himawari': {'sst': ['nc', 'png', 'temp']},
            'sentinel3a': {'sst': ['nc', 'png'], 'chl': ['nc', 'png']},
            'sentinel3b': {'sst': ['nc', 'png'], 'chl': ['nc', 'png']}
        }
    
    def check_current_structure(self) -> Dict:
        """Check current data structure and file counts"""
        print("🔍 Checking current data structure...")
        
        structure_info = {
            'unified': {},
            'legacy': {},
            'migration_needed': False,
            'timestamp': datetime.now().isoformat()
        }
        
        # Check unified structure
        for satellite, params in self.unified_structure.items():
            structure_info['unified'][satellite] = {}
            for param, file_types in params.items():
                structure_info['unified'][satellite][param] = {}
                for file_type in file_types:
                    unified_dir = self.base_dir / satellite / param / file_type
                    file_count = len(list(unified_dir.glob("*.*"))) if unified_dir.exists() else 0
                    structure_info['unified'][satellite][param][file_type] = {
                        'exists': unified_dir.exists(),
                        'file_count': file_count,
                        'path': str(unified_dir)
                    }
        
        # Check legacy structure
        total_legacy_files = 0
        
        # Himawari legacy
        himawari_legacy = self.legacy_dirs['himawari']
        structure_info['legacy']['himawari'] = {}
        
        nc_count = len(list(himawari_legacy['nc'].glob("*.nc"))) if himawari_legacy['nc'].exists() else 0
        png_count = len(list(himawari_legacy['png'].glob("*.png"))) if himawari_legacy['png'].exists() else 0
        temp_count = len(list(himawari_legacy['temp'].glob("*.*"))) if himawari_legacy['temp'].exists() else 0
        
        structure_info['legacy']['himawari'] = {
            'nc': {'file_count': nc_count, 'path': str(himawari_legacy['nc'])},
            'png': {'file_count': png_count, 'path': str(himawari_legacy['png'])},
            'temp': {'file_count': temp_count, 'path': str(himawari_legacy['temp'])}
        }
        total_legacy_files += nc_count + png_count + temp_count
        
        # Sentinel-3 legacy
        for satellite in ['sentinel3a', 'sentinel3b']:
            structure_info['legacy'][satellite] = {}
            satellite_base = Path(f"saternal3/data/eumetview_sentinel3/{satellite}")
            
            for param in ['sst', 'chl']:
                structure_info['legacy'][satellite][param] = {}
                for file_type in ['nc', 'png']:
                    legacy_dir = satellite_base / param / file_type
                    file_count = len(list(legacy_dir.glob(f"*.{file_type}"))) if legacy_dir.exists() else 0
                    structure_info['legacy'][satellite][param][file_type] = {
                        'file_count': file_count,
                        'path': str(legacy_dir)
                    }
                    total_legacy_files += file_count
        
        structure_info['migration_needed'] = total_legacy_files > 0
        structure_info['total_legacy_files'] = total_legacy_files
        
        return structure_info
    
    def print_structure_report(self, structure_info: Dict):
        """Print a formatted report of the current structure"""
        print("\n📊 Data Structure Report")
        print("=" * 50)
        
        print(f"\n🗂️ Unified Structure (data/):")
        for satellite, params in structure_info['unified'].items():
            print(f"  📡 {satellite}:")
            for param, file_types in params.items():
                print(f"    📁 {param}:")
                for file_type, info in file_types.items():
                    status = "✅" if info['exists'] and info['file_count'] > 0 else "📁" if info['exists'] else "❌"
                    print(f"      {status} {file_type}: {info['file_count']} files")
        
        print(f"\n🗂️ Legacy Structure:")
        for satellite, params in structure_info['legacy'].items():
            print(f"  📡 {satellite}:")
            if satellite == 'himawari':
                for file_type, info in params.items():
                    status = "⚠️" if info['file_count'] > 0 else "✅"
                    print(f"    {status} {file_type}: {info['file_count']} files")
            else:
                for param, file_types in params.items():
                    print(f"    📁 {param}:")
                    for file_type, info in file_types.items():
                        status = "⚠️" if info['file_count'] > 0 else "✅"
                        print(f"      {status} {file_type}: {info['file_count']} files")
        
        print(f"\n📈 Summary:")
        print(f"  Total legacy files: {structure_info['total_legacy_files']}")
        print(f"  Migration needed: {'Yes' if structure_info['migration_needed'] else 'No'}")
    
    def migrate_data(self, dry_run: bool = False) -> Dict:
        """Migrate data from legacy to unified structure"""
        print(f"🚀 {'Dry run: ' if dry_run else ''}Migrating data to unified structure...")
        
        migration_report = {
            'migrated_files': 0,
            'created_directories': 0,
            'errors': [],
            'operations': [],
            'dry_run': dry_run,
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            # Create unified directories
            for satellite, params in self.unified_structure.items():
                for param, file_types in params.items():
                    for file_type in file_types:
                        unified_dir = self.base_dir / satellite / param / file_type
                        if not unified_dir.exists():
                            if not dry_run:
                                unified_dir.mkdir(parents=True, exist_ok=True)
                            migration_report['created_directories'] += 1
                            migration_report['operations'].append(f"Created directory: {unified_dir}")
                            print(f"  📁 Created: {unified_dir}")
            
            # Migrate Himawari files
            self._migrate_himawari_files(migration_report, dry_run)
            
            # Migrate Sentinel-3 files
            self._migrate_sentinel3_files(migration_report, dry_run)
            
        except Exception as e:
            error_msg = f"Migration failed: {str(e)}"
            migration_report['errors'].append(error_msg)
            print(f"❌ {error_msg}")
        
        return migration_report
    
    def _migrate_himawari_files(self, migration_report: Dict, dry_run: bool):
        """Migrate Himawari files"""
        print(f"  📡 Migrating Himawari files...")
        
        himawari_legacy = self.legacy_dirs['himawari']
        
        # Migrate NC files
        if himawari_legacy['nc'].exists():
            unified_nc_dir = self.base_dir / "himawari" / "sst" / "nc"
            for nc_file in himawari_legacy['nc'].glob("*.nc"):
                dest_file = unified_nc_dir / nc_file.name
                if not dest_file.exists():
                    if not dry_run:
                        shutil.copy2(nc_file, dest_file)
                    migration_report['migrated_files'] += 1
                    migration_report['operations'].append(f"Copied: {nc_file} -> {dest_file}")
                    print(f"    ✅ Copied: {nc_file.name}")
        
        # Migrate PNG files
        if himawari_legacy['png'].exists():
            unified_png_dir = self.base_dir / "himawari" / "sst" / "png"
            for png_file in himawari_legacy['png'].glob("*.png"):
                dest_file = unified_png_dir / png_file.name
                if not dest_file.exists():
                    if not dry_run:
                        shutil.copy2(png_file, dest_file)
                    migration_report['migrated_files'] += 1
                    migration_report['operations'].append(f"Copied: {png_file} -> {dest_file}")
                    print(f"    ✅ Copied: {png_file.name}")
    
    def _migrate_sentinel3_files(self, migration_report: Dict, dry_run: bool):
        """Migrate Sentinel-3 files"""
        print(f"  📡 Migrating Sentinel-3 files...")
        
        for satellite in ['sentinel3a', 'sentinel3b']:
            print(f"    📡 Migrating {satellite}...")
            satellite_base = Path(f"saternal3/data/eumetview_sentinel3/{satellite}")
            
            if not satellite_base.exists():
                continue
            
            for param in ['sst', 'chl']:
                for file_type in ['nc', 'png']:
                    legacy_dir = satellite_base / param / file_type
                    if legacy_dir.exists():
                        unified_dir = self.base_dir / satellite / param / file_type
                        
                        for file_path in legacy_dir.glob(f"*.{file_type}"):
                            dest_file = unified_dir / file_path.name
                            if not dest_file.exists():
                                if not dry_run:
                                    shutil.copy2(file_path, dest_file)
                                migration_report['migrated_files'] += 1
                                migration_report['operations'].append(f"Copied: {file_path} -> {dest_file}")
                                print(f"      ✅ Copied: {file_path.name}")
    
    def verify_migration(self) -> Dict:
        """Verify that migration was successful"""
        print("🔍 Verifying migration...")
        
        verification_report = {
            'unified_files': 0,
            'legacy_files': 0,
            'missing_files': [],
            'success': True,
            'timestamp': datetime.now().isoformat()
        }
        
        # Count unified files
        for satellite, params in self.unified_structure.items():
            for param, file_types in params.items():
                for file_type in file_types:
                    unified_dir = self.base_dir / satellite / param / file_type
                    if unified_dir.exists():
                        verification_report['unified_files'] += len(list(unified_dir.glob("*.*")))
        
        # Count legacy files that still exist
        himawari_legacy = self.legacy_dirs['himawari']
        if himawari_legacy['nc'].exists():
            verification_report['legacy_files'] += len(list(himawari_legacy['nc'].glob("*.nc")))
        if himawari_legacy['png'].exists():
            verification_report['legacy_files'] += len(list(himawari_legacy['png'].glob("*.png")))
        
        for satellite in ['sentinel3a', 'sentinel3b']:
            satellite_base = Path(f"saternal3/data/eumetview_sentinel3/{satellite}")
            if satellite_base.exists():
                for param in ['sst', 'chl']:
                    for file_type in ['nc', 'png']:
                        legacy_dir = satellite_base / param / file_type
                        if legacy_dir.exists():
                            verification_report['legacy_files'] += len(list(legacy_dir.glob(f"*.{file_type}")))
        
        verification_report['success'] = verification_report['unified_files'] > 0
        
        return verification_report
    
    def print_migration_report(self, migration_report: Dict):
        """Print migration report"""
        print(f"\n📊 Migration Report")
        print("=" * 50)
        print(f"Dry run: {migration_report['dry_run']}")
        print(f"Created directories: {migration_report['created_directories']}")
        print(f"Migrated files: {migration_report['migrated_files']}")
        print(f"Errors: {len(migration_report['errors'])}")
        
        if migration_report['errors']:
            print("\n❌ Errors:")
            for error in migration_report['errors']:
                print(f"  • {error}")
    
    def print_verification_report(self, verification_report: Dict):
        """Print verification report"""
        print(f"\n📊 Verification Report")
        print("=" * 50)
        print(f"Unified structure files: {verification_report['unified_files']}")
        print(f"Legacy files remaining: {verification_report['legacy_files']}")
        print(f"Migration successful: {'✅ Yes' if verification_report['success'] else '❌ No'}")
        
        if verification_report['legacy_files'] > 0:
            print("\n⚠️ Note: Legacy files still exist. You may want to clean them up after verifying the migration.")


def main():
    parser = argparse.ArgumentParser(description='Satellite Data Migration Tool')
    parser.add_argument('--check', action='store_true', help='Check current data structure')
    parser.add_argument('--migrate', action='store_true', help='Migrate data to unified structure')
    parser.add_argument('--verify', action='store_true', help='Verify migration was successful')
    parser.add_argument('--dry-run', action='store_true', help='Perform a dry run (no actual file operations)')
    parser.add_argument('--save-report', type=str, help='Save report to JSON file')
    
    args = parser.parse_args()
    
    if not any([args.check, args.migrate, args.verify]):
        parser.print_help()
        sys.exit(1)
    
    migration_tool = DataMigrationTool()
    
    if args.check:
        structure_info = migration_tool.check_current_structure()
        migration_tool.print_structure_report(structure_info)
        
        if args.save_report:
            with open(args.save_report, 'w') as f:
                json.dump(structure_info, f, indent=2)
            print(f"\n💾 Report saved to: {args.save_report}")
    
    if args.migrate:
        migration_report = migration_tool.migrate_data(dry_run=args.dry_run)
        migration_tool.print_migration_report(migration_report)
        
        if args.save_report:
            filename = args.save_report.replace('.json', '_migration.json')
            with open(filename, 'w') as f:
                json.dump(migration_report, f, indent=2)
            print(f"\n💾 Migration report saved to: {filename}")
    
    if args.verify:
        verification_report = migration_tool.verify_migration()
        migration_tool.print_verification_report(verification_report)
        
        if args.save_report:
            filename = args.save_report.replace('.json', '_verification.json')
            with open(filename, 'w') as f:
                json.dump(verification_report, f, indent=2)
            print(f"\n💾 Verification report saved to: {filename}")


if __name__ == "__main__":
    main()
