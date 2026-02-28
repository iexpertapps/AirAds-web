#!/usr/bin/env python3
"""
Backup Verification System for AirAds User Portal
Verifies backup integrity and generates reports
"""

import os
import sys
import hashlib
import json
import boto3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import django

# Setup Django environment
sys.path.append('/Users/syedsmacbook/Developer/AirAds-web/airaad/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')
django.setup()

from apps.user_portal.models_backup import BackupLog, RecoveryLog
from apps.user_portal.logging import structured_logger
from django.conf import settings
from django.utils import timezone


class BackupVerifier:
    """
    Backup verification and integrity checking system.
    """
    
    def __init__(self):
        self.logger = structured_logger
        
        # AWS S3 configuration
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=getattr(settings, 'AWS_ACCESS_KEY_ID', ''),
            aws_secret_access_key=getattr(settings, 'AWS_SECRET_ACCESS_KEY', ''),
            region_name=getattr(settings, 'AWS_DEFAULT_REGION', 'us-east-1')
        )
        self.backup_bucket = getattr(settings, 'AWS_BACKUP_BUCKET', 'airad-backups')
    
    def verify_recent_backups(self, days: int = 7) -> Dict:
        """Verify backups from the last N days."""
        self.logger.info(f"Starting backup verification for last {days} days")
        
        since = timezone.now() - timedelta(days=days)
        recent_backups = BackupLog.objects.filter(
            started_at__gte=since,
            success=True
        )
        
        verification_results = {
            'total_backups': recent_backups.count(),
            'verified_backups': 0,
            'failed_verifications': 0,
            'verification_details': [],
            'summary': {}
        }
        
        for backup in recent_backups:
            result = self._verify_backup(backup)
            verification_results['verification_details'].append(result)
            
            if result['verified']:
                verification_results['verified_backups'] += 1
            else:
                verification_results['failed_verifications'] += 1
        
        # Calculate summary statistics
        verification_results['summary'] = self._calculate_verification_summary(
            verification_results['verification_details']
        )
        
        self.logger.info(
            "Backup verification completed",
            total_backups=verification_results['total_backups'],
            verified_backups=verification_results['verified_backups'],
            failed_verifications=verification_results['failed_verifications']
        )
        
        return verification_results
    
    def _verify_backup(self, backup: BackupLog) -> Dict:
        """Verify individual backup integrity."""
        verification_result = {
            'backup_id': str(backup.id),
            'backup_name': backup.backup_name,
            'backup_type': backup.backup_type,
            'started_at': backup.started_at.isoformat(),
            'verified': False,
            'checksum_valid': False,
            'files_present': False,
            'errors': [],
            'details': {}
        }
        
        try:
            # Get backup metadata
            metadata = backup.metadata or {}
            
            # Verify each backup component
            components_verified = 0
            total_components = 0
            
            for component, component_data in metadata.items():
                if isinstance(component_data, dict) and 's3_key' in component_data:
                    total_components += 1
                    
                    # Verify S3 object exists
                    if self._verify_s3_object(component_data['s3_key']):
                        components_verified += 1
                        
                        # Verify checksum if available
                        if component_data.get('checksum'):
                            checksum_valid = self._verify_checksum(
                                component_data['s3_key'],
                                component_data['checksum']
                            )
                            if not checksum_valid:
                                verification_result['errors'].append(
                                    f"Checksum mismatch for {component}"
                                )
                            else:
                                verification_result['details'][f'{component}_checksum'] = 'valid'
                    else:
                        verification_result['errors'].append(
                            f"Missing S3 object for {component}"
                        )
            
            # Check if all components are verified
            verification_result['files_present'] = components_verified == total_components
            verification_result['checksum_valid'] = len(verification_result['errors']) == 0
            verification_result['verified'] = (
                verification_result['files_present'] and 
                verification_result['checksum_valid']
            )
            
            # Update backup verification status
            if verification_result['verified']:
                backup.verify_backup('verification_completed')
            else:
                backup.verified = False
                backup.save()
            
        except Exception as e:
            verification_result['errors'].append(f"Verification error: {str(e)}")
            self.logger.error(
                "Backup verification failed",
                backup_id=str(backup.id),
                error=str(e)
            )
        
        return verification_result
    
    def _verify_s3_object(self, s3_key: str) -> bool:
        """Verify S3 object exists."""
        try:
            self.s3_client.head_object(Bucket=self.backup_bucket, Key=s3_key)
            return True
        except Exception:
            return False
    
    def _verify_checksum(self, s3_key: str, expected_checksum: str) -> bool:
        """Verify checksum of S3 object."""
        try:
            # Get object
            response = self.s3_client.get_object(Bucket=self.backup_bucket, Key=s3_key)
            
            # Calculate checksum
            hash_sha256 = hashlib.sha256()
            for chunk in iter(lambda: response['Body'].read(4096), b""):
                hash_sha256.update(chunk)
            
            actual_checksum = hash_sha256.hexdigest()
            
            return actual_checksum == expected_checksum
            
        except Exception as e:
            self.logger.error(
                "Checksum verification failed",
                s3_key=s3_key,
                error=str(e)
            )
            return False
    
    def _calculate_verification_summary(self, verification_details: List[Dict]) -> Dict:
        """Calculate verification summary statistics."""
        summary = {
            'success_rate': 0,
            'component_success_rates': {},
            'common_errors': {},
            'backup_types': {},
            'average_backup_size': 0,
            'total_verified_size': 0
        }
        
        if not verification_details:
            return summary
        
        # Calculate overall success rate
        successful_verifications = sum(1 for v in verification_details if v['verified'])
        summary['success_rate'] = (successful_verifications / len(verification_details)) * 100
        
        # Calculate backup type statistics
        for verification in verification_details:
            backup_type = verification['backup_type']
            if backup_type not in summary['backup_types']:
                summary['backup_types'][backup_type] = {'total': 0, 'verified': 0}
            
            summary['backup_types'][backup_type]['total'] += 1
            if verification['verified']:
                summary['backup_types'][backup_type]['verified'] += 1
        
        # Calculate success rates by backup type
        for backup_type, stats in summary['backup_types'].items():
            if stats['total'] > 0:
                stats['success_rate'] = (stats['verified'] / stats['total']) * 100
        
        # Collect common errors
        all_errors = []
        for verification in verification_details:
            all_errors.extend(verification['errors'])
        
        # Count error frequencies
        error_counts = {}
        for error in all_errors:
            error_counts[error] = error_counts.get(error, 0) + 1
        
        # Sort by frequency
        summary['common_errors'] = dict(
            sorted(error_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        )
        
        return summary
    
    def generate_verification_report(self, days: int = 7) -> str:
        """Generate comprehensive verification report."""
        verification_results = self.verify_recent_backups(days)
        
        report = f"""
# AirAds Backup Verification Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Period: Last {days} days

## Executive Summary
- Total Backups: {verification_results['total_backups']}
- Successfully Verified: {verification_results['verified_backups']}
- Failed Verifications: {verification_results['failed_verifications']}
- Overall Success Rate: {verification_results['summary']['success_rate']:.1f}%

## Backup Type Performance
"""
        
        for backup_type, stats in verification_results['summary']['backup_types'].items():
            report += f"- {backup_type}: {stats['verified']}/{stats['total']} ({stats['success_rate']:.1f}%)\n"
        
        report += "\n## Common Issues\n"
        if verification_results['summary']['common_errors']:
            for error, count in verification_results['summary']['common_errors'].items():
                report += f"- {error}: {count} occurrences\n"
        else:
            report += "- No common issues detected\n"
        
        report += "\n## Detailed Results\n"
        for verification in verification_results['verification_details']:
            status = "✅ VERIFIED" if verification['verified'] else "❌ FAILED"
            report += f"\n### {verification['backup_name']} - {status}\n"
            report += f"- Type: {verification['backup_type']}\n"
            report += f"- Date: {verification['started_at']}\n"
            report += f"- Files Present: {verification['files_present']}\n"
            report += f"- Checksum Valid: {verification['checksum_valid']}\n"
            
            if verification['errors']:
                report += "- Errors:\n"
                for error in verification['errors']:
                    report += f"  - {error}\n"
        
        return report
    
    def save_report(self, report: str, days: int = 7) -> str:
        """Save verification report to file."""
        report_dir = Path("/var/log/airad")
        report_dir.mkdir(exist_ok=True)
        
        report_file = report_dir / f"backup_verification_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        
        with open(report_file, 'w') as f:
            f.write(report)
        
        self.logger.info(
            "Verification report saved",
            report_file=str(report_file)
        )
        
        return str(report_file)


def main():
    """Main verification execution function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='AirAds Backup Verification')
    parser.add_argument('--days', type=int, default=7, help='Days to verify')
    parser.add_argument('--report', action='store_true', help='Generate report')
    parser.add_argument('--save-report', action='store_true', help='Save report to file')
    
    args = parser.parse_args()
    
    verifier = BackupVerifier()
    
    try:
        if args.report or args.save_report:
            report = verifier.generate_verification_report(args.days)
            
            if args.save_report:
                report_file = verifier.save_report(report, args.days)
                print(f"Report saved to: {report_file}")
            else:
                print(report)
        else:
            results = verifier.verify_recent_backups(args.days)
            print(f"Verification completed: {results['verified_backups']}/{results['total_backups']} backups verified")
    
    except Exception as e:
        print(f"Verification failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
