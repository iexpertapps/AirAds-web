#!/usr/bin/env python3
"""
Disaster Recovery Procedures for AirAds User Portal
Comprehensive disaster recovery automation and procedures
"""

import os
import sys
import subprocess
import json
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import boto3
import psycopg2
from redis import Redis
import django

# Setup Django environment
sys.path.append('/Users/syedsmacbook/Developer/AirAds-web/airaad/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')
django.setup()

from apps.user_portal.models_backup import BackupLog, RecoveryLog
from apps.user_portal.logging import structured_logger
from django.conf import settings
from django.utils import timezone


class DisasterRecoveryManager:
    """
    Disaster Recovery Management System.
    Handles automated disaster recovery procedures and failover.
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
        
        # Database configuration
        self.db_config = {
            'host': settings.DATABASES['default']['HOST'],
            'port': settings.DATABASES['default']['PORT'],
            'database': settings.DATABASES['default']['NAME'],
            'user': settings.DATABASES['default']['USER'],
            'password': settings.DATABASES['default']['PASSWORD'],
        }
        
        # Redis configuration
        self.redis_config = {
            'host': settings.CACHES['default']['LOCATION'].split(':')[0],
            'port': int(settings.CACHES['default']['LOCATION'].split(':')[1]),
            'db': int(settings.CACHES['default']['LOCATION'].split('/')[2] if '/' in settings.CACHES['default']['LOCATION'] else 0),
        }
        
        # Recovery thresholds
        self.max_recovery_time = getattr(settings, 'MAX_RECOVERY_TIME', 3600)  # 1 hour
        self.data_loss_threshold = getattr(settings, 'DATA_LOSS_THRESHOLD', 300)  # 5 minutes
    
    def assess_disaster_situation(self) -> Dict:
        """Assess the current disaster situation."""
        assessment = {
            'timestamp': datetime.now().isoformat(),
            'disaster_level': 'NONE',
            'affected_systems': [],
            'data_loss_estimate': None,
            'recovery_time_estimate': None,
            'recommended_actions': [],
            'system_checks': {}
        }
        
        # Check database status
        db_status = self._check_database_status()
        assessment['system_checks']['database'] = db_status
        
        # Check Redis status
        redis_status = self._check_redis_status()
        assessment['system_checks']['redis'] = redis_status
        
        # Check application status
        app_status = self._check_application_status()
        assessment['system_checks']['application'] = app_status
        
        # Determine disaster level
        failed_systems = []
        for system, status in assessment['system_checks'].items():
            if status['status'] == 'CRITICAL' or status['status'] == 'DOWN':
                failed_systems.append(system)
        
        assessment['affected_systems'] = failed_systems
        
        if len(failed_systems) == 0:
            assessment['disaster_level'] = 'NONE'
            assessment['recommended_actions'] = ['No action required']
        elif len(failed_systems) == 1:
            assessment['disaster_level'] = 'MINOR'
            assessment['recovery_time_estimate'] = '15-30 minutes'
            assessment['recommended_actions'] = [f'Recover {failed_systems[0]} system']
        elif len(failed_systems) == 2:
            assessment['disaster_level'] = 'MAJOR'
            assessment['recovery_time_estimate'] = '30-60 minutes'
            assessment['recommended_actions'] = ['Recover multiple systems', 'Consider failover']
        else:
            assessment['disaster_level'] = 'CATASTROPHIC'
            assessment['recovery_time_estimate'] = '1-4 hours'
            assessment['recommended_actions'] = ['Full system recovery', 'Activate disaster recovery plan']
        
        # Estimate data loss
        assessment['data_loss_estimate'] = self._estimate_data_loss(assessment['system_checks'])
        
        self.logger.info(
            "Disaster assessment completed",
            disaster_level=assessment['disaster_level'],
            affected_systems=assessment['affected_systems']
        )
        
        return assessment
    
    def _check_database_status(self) -> Dict:
        """Check database system status."""
        status = {
            'status': 'UNKNOWN',
            'connectivity': False,
            'replication_lag': None,
            'last_backup': None,
            'error': None
        }
        
        try:
            # Test connectivity
            conn = psycopg2.connect(**self.db_config, connect_timeout=5)
            cursor = conn.cursor()
            
            # Simple query
            cursor.execute("SELECT 1")
            cursor.fetchone()
            
            status['connectivity'] = True
            
            # Check replication lag if this is a replica
            cursor.execute("SELECT pg_is_in_recovery()")
            in_recovery = cursor.fetchone()[0]
            
            if in_recovery:
                cursor.execute("""
                    SELECT EXTRACT(EPOCH FROM (now() - pg_last_xact_replay_timestamp())) AS lag_seconds
                """)
                lag_result = cursor.fetchone()
                if lag_result and lag_result[0]:
                    status['replication_lag'] = int(lag_result[0])
            
            # Get last successful backup
            last_backup = BackupLog.objects.filter(
                backup_type='DATABASE',
                success=True
            ).order_by('-started_at').first()
            
            if last_backup:
                status['last_backup'] = last_backup.started_at.isoformat()
            
            conn.close()
            
            # Determine status
            if status['connectivity']:
                if status['replication_lag'] and status['replication_lag'] > 300:  # 5 minutes
                    status['status'] = 'DEGRADED'
                else:
                    status['status'] = 'HEALTHY'
            else:
                status['status'] = 'DOWN'
                
        except Exception as e:
            status['status'] = 'CRITICAL'
            status['error'] = str(e)
            self.logger.error("Database status check failed", error=str(e))
        
        return status
    
    def _check_redis_status(self) -> Dict:
        """Check Redis system status."""
        status = {
            'status': 'UNKNOWN',
            'connectivity': False,
            'memory_usage': None,
            'last_backup': None,
            'error': None
        }
        
        try:
            redis_client = Redis(**self.redis_config, socket_timeout=5)
            
            # Test connectivity
            pong = redis_client.ping()
            status['connectivity'] = pong
            
            if pong:
                # Get memory usage
                info = redis_client.info()
                used_memory = info.get('used_memory', 0)
                max_memory = info.get('maxmemory', 0)
                
                if max_memory > 0:
                    memory_usage_percent = (used_memory / max_memory) * 100
                    status['memory_usage'] = round(memory_usage_percent, 2)
                
                # Get last successful backup
                last_backup = BackupLog.objects.filter(
                    backup_type='REDIS',
                    success=True
                ).order_by('-started_at').first()
                
                if last_backup:
                    status['last_backup'] = last_backup.started_at.isoformat()
            
            # Determine status
            if status['connectivity']:
                if status['memory_usage'] and status['memory_usage'] > 90:
                    status['status'] = 'DEGRADED'
                else:
                    status['status'] = 'HEALTHY'
            else:
                status['status'] = 'DOWN'
                
        except Exception as e:
            status['status'] = 'CRITICAL'
            status['error'] = str(e)
            self.logger.error("Redis status check failed", error=str(e))
        
        return status
    
    def _check_application_status(self) -> Dict:
        """Check application system status."""
        status = {
            'status': 'UNKNOWN',
            'web_server': False,
            'application_server': False,
            'error': None
        }
        
        try:
            # Check web server (simplified)
            import requests
            response = requests.get('http://localhost:8000/health/', timeout=5)
            
            if response.status_code == 200:
                status['web_server'] = True
                status['application_server'] = True
                status['status'] = 'HEALTHY'
            else:
                status['status'] = 'DEGRADED'
                
        except Exception as e:
            status['status'] = 'DOWN'
            status['error'] = str(e)
            self.logger.error("Application status check failed", error=str(e))
        
        return status
    
    def _estimate_data_loss(self, system_checks: Dict) -> Dict:
        """Estimate potential data loss."""
        data_loss = {
            'database_loss': None,
            'redis_loss': None,
            'total_loss_minutes': 0
        }
        
        # Estimate database data loss
        db_status = system_checks.get('database', {})
        if db_status.get('last_backup'):
            last_backup_time = datetime.fromisoformat(db_status['last_backup'])
            time_diff = datetime.now() - last_backup_time
            data_loss['database_loss'] = int(time_diff.total_seconds() / 60)
            data_loss['total_loss_minutes'] += data_loss['database_loss']
        
        # Estimate Redis data loss
        redis_status = system_checks.get('redis', {})
        if redis_status.get('last_backup'):
            last_backup_time = datetime.fromisoformat(redis_status['last_backup'])
            time_diff = datetime.now() - last_backup_time
            data_loss['redis_loss'] = int(time_diff.total_seconds() / 60)
            data_loss['total_loss_minutes'] += data_loss['redis_loss']
        
        return data_loss
    
    def initiate_recovery(self, disaster_assessment: Dict) -> RecoveryLog:
        """Initiate disaster recovery based on assessment."""
        recovery_name = f"disaster_recovery_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Create recovery log
        recovery_log = RecoveryLog.initiate_recovery(
            recovery_type='DISASTER',
            recovery_name=recovery_name,
            source_location='disaster_recovery',
            disaster_level=disaster_assessment['disaster_level']
        )
        
        try:
            self.logger.info(
                "Initiating disaster recovery",
                recovery_name=recovery_name,
                disaster_level=disaster_assessment['disaster_level'],
                affected_systems=disaster_assessment['affected_systems']
            )
            
            # Start recovery process
            recovery_log.start_recovery()
            
            # Execute recovery steps based on affected systems
            recovery_results = {}
            
            if 'database' in disaster_assessment['affected_systems']:
                recovery_results['database'] = self._recover_database(recovery_log)
            
            if 'redis' in disaster_assessment['affected_systems']:
                recovery_results['redis'] = self._recover_redis(recovery_log)
            
            if 'application' in disaster_assessment['affected_systems']:
                recovery_results['application'] = self._recover_application(recovery_log)
            
            # Calculate totals
            total_records = sum(result.get('records', 0) for result in recovery_results.values())
            total_files = sum(result.get('files', 0) for result in recovery_results.values())
            
            # Complete recovery
            recovery_log.complete_recovery(
                records_recovered=total_records,
                files_recovered=total_files,
                metadata=recovery_results
            )
            
            self.logger.info(
                "Disaster recovery completed",
                recovery_name=recovery_name,
                records_recovered=total_records,
                files_recovered=total_files
            )
            
            return recovery_log
            
        except Exception as e:
            recovery_log.fail_recovery(
                error_message=str(e),
                error_code=type(e).__name__
            )
            
            self.logger.error(
                "Disaster recovery failed",
                recovery_name=recovery_name,
                error=str(e)
            )
            
            raise
    
    def _recover_database(self, recovery_log: RecoveryLog) -> Dict:
        """Recover database from backup."""
        self.logger.info("Starting database recovery")
        
        result = {
            'status': 'FAILED',
            'records': 0,
            'files': 0,
            'backup_used': None,
            'error': None
        }
        
        try:
            # Find most recent successful database backup
            latest_backup = BackupLog.objects.filter(
                backup_type='DATABASE',
                success=True
            ).order_by('-started_at').first()
            
            if not latest_backup:
                raise Exception("No suitable database backup found")
            
            result['backup_used'] = latest_backup.backup_name
            
            # Download backup from S3
            backup_dir = Path('/tmp/disaster_recovery')
            backup_dir.mkdir(exist_ok=True)
            
            backup_file = backup_dir / f"{latest_backup.backup_name}_database.sql.gz"
            s3_key = f"{latest_backup.backup_name}/database.sql.gz"
            
            self.s3_client.download_file(
                self.backup_bucket,
                s3_key,
                str(backup_file)
            )
            
            # Restore database
            cmd = [
                'gunzip',
                '-c',
                str(backup_file)
            ]
            
            restore_cmd = [
                'psql',
                f"--host={self.db_config['host']}",
                f"--port={self.db_config['port']}",
                f"--username={self.db_config['user']}",
                f"--dbname={self.db_config['database']}"
            ]
            
            # Pipe gunzip to psql
            gunzip_proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
            psql_proc = subprocess.Popen(restore_cmd, stdin=gunzip_proc.stdout, env={
                'PGPASSWORD': self.db_config['password']
            })
            
            gunzip_proc.stdout.close()
            psql_proc.communicate()
            
            if psql_proc.returncode != 0:
                raise Exception("Database restore failed")
            
            # Verify recovery
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'")
            table_count = cursor.fetchone()[0]
            conn.close()
            
            result['status'] = 'SUCCESS'
            result['records'] = table_count
            result['files'] = 1
            
            # Cleanup
            backup_file.unlink(missing_ok=True)
            
        except Exception as e:
            result['error'] = str(e)
            self.logger.error("Database recovery failed", error=str(e))
            raise
        
        return result
    
    def _recover_redis(self, recovery_log: RecoveryLog) -> Dict:
        """Recover Redis from backup."""
        self.logger.info("Starting Redis recovery")
        
        result = {
            'status': 'FAILED',
            'records': 0,
            'files': 0,
            'backup_used': None,
            'error': None
        }
        
        try:
            # Find most recent successful Redis backup
            latest_backup = BackupLog.objects.filter(
                backup_type='REDIS',
                success=True
            ).order_by('-started_at').first()
            
            if not latest_backup:
                raise Exception("No suitable Redis backup found")
            
            result['backup_used'] = latest_backup.backup_name
            
            # Download backup from S3
            backup_dir = Path('/tmp/disaster_recovery')
            backup_dir.mkdir(exist_ok=True)
            
            backup_file = backup_dir / f"{latest_backup.backup_name}_redis.rdb.gz"
            s3_key = f"{latest_backup.backup_name}/redis.rdb.gz"
            
            self.s3_client.download_file(
                self.backup_bucket,
                s3_key,
                str(backup_file)
            )
            
            # Extract backup
            extracted_file = backup_file.with_suffix('.rdb')
            subprocess.run(['gunzip', str(backup_file), '-c'], stdout=open(extracted_file, 'wb'), check=True)
            
            # Stop Redis
            subprocess.run(['systemctl', 'stop', 'redis'], check=True)
            
            # Replace RDB file
            redis_data_dir = '/var/lib/redis'
            subprocess.run(['cp', str(extracted_file), f'{redis_data_dir}/dump.rdb'], check=True)
            subprocess.run(['chown', 'redis:redis', f'{redis_data_dir}/dump.rdb'], check=True)
            
            # Start Redis
            subprocess.run(['systemctl', 'start', 'redis'], check=True)
            
            # Verify recovery
            redis_client = Redis(**self.redis_config)
            info = redis_client.info()
            keys_count = info.get('db0', {}).get('keys', 0)
            
            result['status'] = 'SUCCESS'
            result['records'] = keys_count
            result['files'] = 1
            
            # Cleanup
            backup_file.unlink(missing_ok=True)
            extracted_file.unlink(missing_ok=True)
            
        except Exception as e:
            result['error'] = str(e)
            self.logger.error("Redis recovery failed", error=str(e))
            raise
        
        return result
    
    def _recover_application(self, recovery_log: RecoveryLog) -> Dict:
        """Recover application services."""
        self.logger.info("Starting application recovery")
        
        result = {
            'status': 'FAILED',
            'records': 0,
            'files': 0,
            'services_restarted': [],
            'error': None
        }
        
        try:
            services = ['nginx', 'gunicorn', 'celery']
            
            for service in services:
                try:
                    # Restart service
                    subprocess.run(['systemctl', 'restart', service], check=True)
                    result['services_restarted'].append(service)
                    
                    # Wait for service to start
                    time.sleep(2)
                    
                    # Check service status
                    status_result = subprocess.run(['systemctl', 'is-active', service], capture_output=True, text=True)
                    if status_result.stdout.strip() == 'active':
                        self.logger.info(f"Service {service} recovered successfully")
                    else:
                        self.logger.warning(f"Service {service} status: {status_result.stdout.strip()}")
                
                except subprocess.CalledProcessError as e:
                    self.logger.error(f"Failed to restart service {service}", error=str(e))
            
            if len(result['services_restarted']) == len(services):
                result['status'] = 'SUCCESS'
            
        except Exception as e:
            result['error'] = str(e)
            self.logger.error("Application recovery failed", error=str(e))
            raise
        
        return result
    
    def generate_recovery_report(self, recovery_log: RecoveryLog) -> str:
        """Generate comprehensive recovery report."""
        report = f"""
# AirAds Disaster Recovery Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Recovery Summary
- Recovery Name: {recovery_log.recovery_name}
- Recovery Type: {recovery_log.recovery_type}
- Status: {recovery_log.status}
- Success: {recovery_log.success}
- Duration: {recovery_log.duration_seconds} seconds

## Recovery Details
- Initiated: {recovery_log.initiated_at.strftime('%Y-%m-%d %H:%M:%S')}
- Started: {recovery_log.started_at.strftime('%Y-%m-%d %H:%M:%S') if recovery_log.started_at else 'N/A'}
- Completed: {recovery_log.completed_at.strftime('%Y-%m-%d %H:%M:%S') if recovery_log.completed_at else 'N/A'}

## Recovery Statistics
- Records Recovered: {recovery_log.records_recovered}
- Files Recovered: {recovery_log.files_recovered}
- Bytes Recovered: {recovery_log.bytes_recovered}

## Source Information
- Source Location: {recovery_log.source_location}
- Source Timestamp: {recovery_log.source_timestamp.strftime('%Y-%m-%d %H:%M:%S')}
- Source Backup: {recovery_log.source_backup.backup_name if recovery_log.source_backup else 'N/A'}

## Verification
- Verified: {recovery_log.verified}
- Verification Date: {recovery_log.verification_date.strftime('%Y-%m-%d %H:%M:%S') if recovery_log.verification_date else 'N/A'}
- Verification Checksum: {recovery_log.verification_checksum}

## Error Information
"""
        
        if recovery_log.error_message:
            report += f"- Error Message: {recovery_log.error_message}\n"
            report += f"- Error Code: {recovery_log.error_code}\n"
        else:
            report += "- No errors occurred\n"
        
        report += "\n## Metadata\n"
        if recovery_log.metadata:
            for key, value in recovery_log.metadata.items():
                report += f"- {key}: {value}\n"
        
        return report


def main():
    """Main disaster recovery execution function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='AirAds Disaster Recovery')
    parser.add_argument('--assess', action='store_true', help='Assess disaster situation')
    parser.add_argument('--recover', action='store_true', help='Initiate recovery')
    parser.add_argument('--report', help='Generate report for recovery ID')
    
    args = parser.parse_args()
    
    recovery_manager = DisasterRecoveryManager()
    
    try:
        if args.assess:
            assessment = recovery_manager.assess_disaster_situation()
            print(json.dumps(assessment, indent=2, default=str))
        
        elif args.recover:
            assessment = recovery_manager.assess_disaster_situation()
            
            if assessment['disaster_level'] == 'NONE':
                print("No disaster detected. No recovery needed.")
                return
            
            recovery_log = recovery_manager.initiate_recovery(assessment)
            print(f"Recovery initiated: {recovery_log.recovery_name}")
            print(f"Status: {recovery_log.status}")
        
        elif args.report:
            try:
                recovery_log = RecoveryLog.objects.get(recovery_name=args.report)
                report = recovery_manager.generate_recovery_report(recovery_log)
                print(report)
            except RecoveryLog.DoesNotExist:
                print(f"Recovery log not found: {args.report}")
                sys.exit(1)
        
        else:
            print("Please specify an action: --assess, --recover, or --report")
            sys.exit(1)
    
    except Exception as e:
        print(f"Disaster recovery failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
