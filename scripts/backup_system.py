#!/usr/bin/env python3
"""
Automated Backup System for AirAds User Portal
Production-ready backup scripts with monitoring and alerting
"""

import os
import sys
import subprocess
import logging
import json
import hashlib
import gzip
import shutil
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


class BackupSystem:
    """
    Comprehensive backup system for AirAds User Portal.
    Handles database, Redis, media files, and configuration backups.
    """
    
    def __init__(self):
        self.logger = structured_logger
        self.backup_dir = Path('/tmp/airad_backups')
        self.backup_dir.mkdir(exist_ok=True)
        
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
    
    def run_full_backup(self) -> BackupLog:
        """Run complete system backup."""
        backup_name = f"airad_full_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        storage_location = f"s3://{self.backup_bucket}/{backup_name}/"
        
        # Start backup log
        backup_log = BackupLog.start_backup(
            backup_type='FULL',
            backup_name=backup_name,
            storage_location=storage_location,
            backup_method='AUTOMATED',
            retention_days=30
        )
        
        try:
            self.logger.info(
                "Starting full system backup",
                backup_name=backup_name,
                backup_id=str(backup_log.id)
            )
            
            # Backup components
            db_result = self._backup_database(backup_log)
            redis_result = self._backup_redis(backup_log)
            media_result = self._backup_media(backup_log)
            config_result = self._backup_config(backup_log)
            
            # Calculate totals
            total_size = db_result['size'] + redis_result['size'] + media_result['size'] + config_result['size']
            total_files = db_result['files'] + redis_result['files'] + media_result['files'] + config_result['files']
            
            # Complete backup
            backup_log.complete_backup(
                backup_size_bytes=total_size,
                files_count=total_files,
                records_count=db_result['records'],
                metadata={
                    'database': db_result,
                    'redis': redis_result,
                    'media': media_result,
                    'config': config_result
                }
            )
            
            self.logger.info(
                "Full backup completed successfully",
                backup_name=backup_name,
                backup_id=str(backup_log.id),
                total_size_bytes=total_size,
                total_files=total_files
            )
            
            return backup_log
            
        except Exception as e:
            backup_log.fail_backup(
                error_message=str(e),
                error_code=type(e).__name__
            )
            
            self.logger.error(
                "Full backup failed",
                backup_name=backup_name,
                backup_id=str(backup_log.id),
                error=str(e),
                error_type=type(e).__name__
            )
            
            raise
    
    def _backup_database(self, backup_log: BackupLog) -> Dict:
        """Backup PostgreSQL database."""
        self.logger.info("Starting database backup")
        
        backup_file = self.backup_dir / f"{backup_log.backup_name}_database.sql"
        compressed_file = backup_file.with_suffix('.sql.gz')
        
        try:
            # Create database dump
            cmd = [
                'pg_dump',
                f"--host={self.db_config['host']}",
                f"--port={self.db_config['port']}",
                f"--username={self.db_config['user']}",
                f"--dbname={self.db_config['database']}",
                '--no-password',
                '--verbose',
                '--clean',
                '--if-exists',
                '--format=custom',
                str(backup_file)
            ]
            
            env = os.environ.copy()
            env['PGPASSWORD'] = self.db_config['password']
            
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=3600  # 1 hour timeout
            )
            
            if result.returncode != 0:
                raise Exception(f"pg_dump failed: {result.stderr}")
            
            # Compress backup
            with open(backup_file, 'rb') as f_in:
                with gzip.open(compressed_file, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            # Calculate checksum
            checksum = self._calculate_file_checksum(compressed_file)
            
            # Upload to S3
            s3_key = f"{backup_log.backup_name}/database.sql.gz"
            self.s3_client.upload_file(
                str(compressed_file),
                self.backup_bucket,
                s3_key
            )
            
            # Get file info
            file_size = compressed_file.stat().st_size
            
            # Get record count
            record_count = self._get_database_record_count()
            
            # Cleanup local files
            backup_file.unlink(missing_ok=True)
            compressed_file.unlink(missing_ok=True)
            
            return {
                'size': file_size,
                'files': 1,
                'records': record_count,
                'checksum': checksum,
                's3_key': s3_key
            }
            
        except Exception as e:
            self.logger.error("Database backup failed", error=str(e))
            raise
    
    def _backup_redis(self, backup_log: BackupLog) -> Dict:
        """Backup Redis data."""
        self.logger.info("Starting Redis backup")
        
        backup_file = self.backup_dir / f"{backup_log.backup_name}_redis.rdb"
        
        try:
            # Connect to Redis
            redis_client = Redis(**self.redis_config)
            
            # Save Redis data
            redis_client.save()
            
            # Wait for save to complete
            lastsave = redis_client.lastsave()
            while redis_client.lastsave() == lastsave:
                import time
                time.sleep(1)
            
            # Copy RDB file
            rdb_path = redis_client.config_get('dir')['dir']
            rdb_file = os.path.join(rdb_path, 'dump.rdb')
            
            shutil.copy2(rdb_file, backup_file)
            
            # Compress backup
            compressed_file = backup_file.with_suffix('.rdb.gz')
            with open(backup_file, 'rb') as f_in:
                with gzip.open(compressed_file, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            # Calculate checksum
            checksum = self._calculate_file_checksum(compressed_file)
            
            # Upload to S3
            s3_key = f"{backup_log.backup_name}/redis.rdb.gz"
            self.s3_client.upload_file(
                str(compressed_file),
                self.backup_bucket,
                s3_key
            )
            
            # Get file info
            file_size = compressed_file.stat().st_size
            
            # Get Redis info
            redis_info = redis_client.info()
            keys_count = redis_info.get('db0', {}).get('keys', 0)
            
            # Cleanup local files
            backup_file.unlink(missing_ok=True)
            compressed_file.unlink(missing_ok=True)
            
            return {
                'size': file_size,
                'files': 1,
                'records': keys_count,
                'checksum': checksum,
                's3_key': s3_key
            }
            
        except Exception as e:
            self.logger.error("Redis backup failed", error=str(e))
            raise
    
    def _backup_media(self, backup_log: BackupLog) -> Dict:
        """Backup media files."""
        self.logger.info("Starting media backup")
        
        try:
            media_dir = Path(settings.MEDIA_ROOT)
            if not media_dir.exists():
                return {'size': 0, 'files': 0, 'records': 0}
            
            # Create tar archive
            backup_file = self.backup_dir / f"{backup_log.backup_name}_media.tar.gz"
            
            # Create compressed tar archive
            shutil.make_archive(
                str(backup_file.with_suffix('')),
                'gztar',
                media_dir.parent,
                media_dir.name
            )
            
            # Calculate checksum
            checksum = self._calculate_file_checksum(backup_file)
            
            # Upload to S3
            s3_key = f"{backup_log.backup_name}/media.tar.gz"
            self.s3_client.upload_file(
                str(backup_file),
                self.backup_bucket,
                s3_key
            )
            
            # Get file info
            file_size = backup_file.stat().st_size
            files_count = sum(1 for _ in media_dir.rglob('*') if _.is_file())
            
            # Cleanup local file
            backup_file.unlink(missing_ok=True)
            
            return {
                'size': file_size,
                'files': files_count,
                'records': 0,
                'checksum': checksum,
                's3_key': s3_key
            }
            
        except Exception as e:
            self.logger.error("Media backup failed", error=str(e))
            raise
    
    def _backup_config(self, backup_log: BackupLog) -> Dict:
        """Backup configuration files."""
        self.logger.info("Starting configuration backup")
        
        try:
            config_data = {
                'django_settings': {
                    'DEBUG': settings.DEBUG,
                    'ALLOWED_HOSTS': settings.ALLOWED_HOSTS,
                    'DATABASES': {
                        'default': {
                            'HOST': settings.DATABASES['default']['HOST'],
                            'PORT': settings.DATABASES['default']['PORT'],
                            'NAME': settings.DATABASES['default']['NAME'],
                        }
                    },
                    'CACHES': {
                        'default': {
                            'LOCATION': settings.CACHES['default']['LOCATION'],
                        }
                    }
                },
                'environment': dict(os.environ),
                'backup_timestamp': timezone.now().isoformat()
            }
            
            # Save to JSON file
            backup_file = self.backup_dir / f"{backup_log.backup_name}_config.json"
            with open(backup_file, 'w') as f:
                json.dump(config_data, f, indent=2, default=str)
            
            # Compress backup
            compressed_file = backup_file.with_suffix('.json.gz')
            with open(backup_file, 'rb') as f_in:
                with gzip.open(compressed_file, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            # Calculate checksum
            checksum = self._calculate_file_checksum(compressed_file)
            
            # Upload to S3
            s3_key = f"{backup_log.backup_name}/config.json.gz"
            self.s3_client.upload_file(
                str(compressed_file),
                self.backup_bucket,
                s3_key
            )
            
            # Get file info
            file_size = compressed_file.stat().st_size
            
            # Cleanup local files
            backup_file.unlink(missing_ok=True)
            compressed_file.unlink(missing_ok=True)
            
            return {
                'size': file_size,
                'files': 1,
                'records': 0,
                'checksum': checksum,
                's3_key': s3_key
            }
            
        except Exception as e:
            self.logger.error("Configuration backup failed", error=str(e))
            raise
    
    def _calculate_file_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of file."""
        hash_sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    
    def _get_database_record_count(self) -> int:
        """Get total record count from database."""
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()
            
            # Get all tables
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                AND table_type = 'BASE TABLE'
            """)
            
            tables = cursor.fetchall()
            total_count = 0
            
            for (table_name,) in tables:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    count = cursor.fetchone()[0]
                    total_count += count
                except Exception:
                    continue  # Skip tables we can't count
            
            conn.close()
            return total_count
            
        except Exception:
            return 0
    
    def cleanup_expired_backups(self) -> int:
        """Clean up expired backups from S3."""
        self.logger.info("Starting expired backup cleanup")
        
        try:
            # Get expired backup logs
            expired_backups = BackupLog.objects.filter(
                expires_at__lt=timezone.now()
            )
            
            deleted_count = 0
            for backup in expired_backups:
                try:
                    # Delete from S3
                    objects = self.s3_client.list_objects_v2(
                        Bucket=self.backup_bucket,
                        Prefix=f"{backup.backup_name}/"
                    )
                    
                    for obj in objects.get('Contents', []):
                        self.s3_client.delete_object(
                            Bucket=self.backup_bucket,
                            Key=obj['Key']
                        )
                    
                    # Delete log entry
                    backup.delete()
                    deleted_count += 1
                    
                except Exception as e:
                    self.logger.error(
                        "Failed to delete expired backup",
                        backup_name=backup.backup_name,
                        error=str(e)
                    )
            
            self.logger.info(
                "Expired backup cleanup completed",
                deleted_count=deleted_count
            )
            
            return deleted_count
            
        except Exception as e:
            self.logger.error("Backup cleanup failed", error=str(e))
            return 0


def main():
    """Main backup execution function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='AirAds Backup System')
    parser.add_argument('--type', choices=['full', 'database', 'redis', 'media', 'config'], 
                       default='full', help='Backup type')
    parser.add_argument('--cleanup', action='store_true', help='Clean up expired backups')
    
    args = parser.parse_args()
    
    backup_system = BackupSystem()
    
    if args.cleanup:
        deleted_count = backup_system.cleanup_expired_backups()
        print(f"Cleaned up {deleted_count} expired backups")
        return
    
    try:
        if args.type == 'full':
            backup_log = backup_system.run_full_backup()
            print(f"Full backup completed: {backup_log.backup_name}")
        else:
            print(f"Backup type '{args.type}' not yet implemented")
    
    except Exception as e:
        print(f"Backup failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
