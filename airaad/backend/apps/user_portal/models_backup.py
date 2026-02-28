from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.conf import settings
import uuid
import json

User = get_user_model()


class BackupLog(models.Model):
    """
    Centralized backup logging model.
    Tracks all backup operations for monitoring and compliance.
    """
    
    BACKUP_TYPES = [
        ('DATABASE', 'Database Backup'),
        ('REDIS', 'Redis Backup'),
        ('MEDIA', 'Media Files Backup'),
        ('CONFIG', 'Configuration Backup'),
        ('FULL', 'Full System Backup'),
    ]
    
    BACKUP_METHODS = [
        ('AUTOMATED', 'Automated Backup'),
        ('MANUAL', 'Manual Backup'),
        ('SCHEDULED', 'Scheduled Backup'),
    ]
    
    STATUS_CHOICES = [
        ('STARTED', 'Started'),
        ('RUNNING', 'Running'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    # Backup identification
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    backup_type = models.CharField(max_length=20, choices=BACKUP_TYPES, db_index=True)
    backup_method = models.CharField(max_length=20, choices=BACKUP_METHODS, default='AUTOMATED')
    
    # Backup details
    backup_name = models.CharField(max_length=200, db_index=True)
    description = models.TextField(blank=True)
    
    # Storage information
    storage_location = models.CharField(max_length=500)
    storage_provider = models.CharField(max_length=50, default='AWS_S3')
    backup_size_bytes = models.BigIntegerField(default=0)
    compressed_size_bytes = models.BigIntegerField(default=0)
    
    # Timing information
    started_at = models.DateTimeField(db_index=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.IntegerField(null=True, blank=True)
    
    # Status and results
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='STARTED', db_index=True)
    success = models.BooleanField(default=False, db_index=True)
    error_message = models.TextField(blank=True)
    error_code = models.CharField(max_length=50, blank=True)
    
    # Backup statistics
    files_count = models.IntegerField(default=0)
    records_count = models.IntegerField(default=0)
    tables_count = models.IntegerField(default=0)
    
    # Verification
    checksum = models.CharField(max_length=128, blank=True)
    verified = models.BooleanField(default=False)
    verification_date = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    metadata = models.JSONField(default=dict, blank=True)
    
    # Retention
    retention_days = models.IntegerField(default=30)
    expires_at = models.DateTimeField(null=True, blank=True, db_index=True)
    
    # Audit
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='created_backups'
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_portal_backup_logs'
        indexes = [
            models.Index(fields=['backup_type', 'status', 'started_at']),
            models.Index(fields=['storage_provider', 'started_at']),
            models.Index(fields=['success', 'started_at']),
            models.Index(fields=['expires_at', 'backup_type']),
            models.Index(fields=['created_by', 'started_at']),
        ]
        ordering = ['-started_at']
    
    def __str__(self):
        return f"{self.backup_type}: {self.backup_name} ({self.status})"
    
    def save(self, *args, **kwargs):
        # Auto-calculate duration if completed
        if self.completed_at and self.started_at and not self.duration_seconds:
            self.duration_seconds = int((self.completed_at - self.started_at).total_seconds())
        
        # Auto-set expiry date
        if self.retention_days and not self.expires_at:
            self.expires_at = self.started_at + timezone.timedelta(days=self.retention_days)
        
        super().save(*args, **kwargs)
    
    @classmethod
    def start_backup(cls, backup_type, backup_name, storage_location, **kwargs):
        """Start a new backup operation."""
        backup = cls.objects.create(
            backup_type=backup_type,
            backup_name=backup_name,
            storage_location=storage_location,
            started_at=timezone.now(),
            metadata=kwargs
        )
        return backup
    
    def complete_backup(self, backup_size_bytes=0, files_count=0, records_count=0, **kwargs):
        """Mark backup as completed."""
        self.status = 'COMPLETED'
        self.success = True
        self.completed_at = timezone.now()
        self.backup_size_bytes = backup_size_bytes
        self.files_count = files_count
        self.records_count = records_count
        
        if kwargs:
            self.metadata.update(kwargs)
        
        self.save()
    
    def fail_backup(self, error_message, error_code=None, **kwargs):
        """Mark backup as failed."""
        self.status = 'FAILED'
        self.success = False
        self.completed_at = timezone.now()
        self.error_message = error_message
        self.error_code = error_code
        
        if kwargs:
            self.metadata.update(kwargs)
        
        self.save()
    
    def verify_backup(self, checksum):
        """Verify backup integrity."""
        self.checksum = checksum
        self.verified = True
        self.verification_date = timezone.now()
        self.save()
    
    @classmethod
    def get_backup_statistics(cls, days=30):
        """Get backup statistics for the last N days."""
        from django.utils import timezone
        from django.db.models import Count, Sum, Avg
        
        since = timezone.now() - timezone.timedelta(days=days)
        
        stats = cls.objects.filter(
            started_at__gte=since
        ).aggregate(
            total_backups=Count('id'),
            successful_backups=Count('id', filter=models.Q(success=True)),
            failed_backups=Count('id', filter=models.Q(success=False)),
            total_size=Sum('backup_size_bytes'),
            avg_duration=Avg('duration_seconds'),
            avg_size=Avg('backup_size_bytes'),
        )
        
        # Calculate success rate
        if stats['total_backups'] > 0:
            stats['success_rate'] = (stats['successful_backups'] / stats['total_backups']) * 100
        else:
            stats['success_rate'] = 0
        
        return stats
    
    @classmethod
    def cleanup_expired_backups(cls):
        """Delete expired backup logs."""
        from django.utils import timezone
        
        expired_backups = cls.objects.filter(
            expires_at__lt=timezone.now()
        )
        
        count = expired_backups.count()
        expired_backups.delete()
        
        return count


class RecoveryLog(models.Model):
    """
    Recovery operation logging model.
    Tracks all data recovery operations for audit and analysis.
    """
    
    RECOVERY_TYPES = [
        ('DATABASE', 'Database Recovery'),
        ('REDIS', 'Redis Recovery'),
        ('MEDIA', 'Media Recovery'),
        ('CONFIG', 'Configuration Recovery'),
        ('POINT_IN_TIME', 'Point-in-Time Recovery'),
        ('PARTIAL', 'Partial Recovery'),
    ]
    
    RECOVERY_METHODS = [
        ('AUTOMATIC', 'Automatic Recovery'),
        ('MANUAL', 'Manual Recovery'),
        ('SCRIPTED', 'Scripted Recovery'),
    ]
    
    STATUS_CHOICES = [
        ('INITIATED', 'Initiated'),
        ('RUNNING', 'Running'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('CANCELLED', 'Cancelled'),
        ('ROLLED_BACK', 'Rolled Back'),
    ]
    
    # Recovery identification
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recovery_type = models.CharField(max_length=20, choices=RECOVERY_TYPES, db_index=True)
    recovery_method = models.CharField(max_length=20, choices=RECOVERY_METHODS)
    
    # Source information
    source_backup = models.ForeignKey(
        BackupLog,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='recoveries'
    )
    source_location = models.CharField(max_length=500)
    source_timestamp = models.DateTimeField()
    
    # Recovery details
    recovery_name = models.CharField(max_length=200, db_index=True)
    description = models.TextField(blank=True)
    
    # Target information
    target_database = models.CharField(max_length=100, blank=True)
    target_tables = models.JSONField(default=list, blank=True)
    target_location = models.CharField(max_length=500, blank=True)
    
    # Timing information
    initiated_at = models.DateTimeField(db_index=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.IntegerField(null=True, blank=True)
    
    # Status and results
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='INITIATED', db_index=True)
    success = models.BooleanField(default=False, db_index=True)
    error_message = models.TextField(blank=True)
    error_code = models.CharField(max_length=50, blank=True)
    
    # Recovery statistics
    records_recovered = models.IntegerField(default=0)
    files_recovered = models.IntegerField(default=0)
    tables_recovered = models.IntegerField(default=0)
    bytes_recovered = models.BigIntegerField(default=0)
    
    # Verification
    verified = models.BooleanField(default=False)
    verification_date = models.DateTimeField(null=True, blank=True)
    verification_checksum = models.CharField(max_length=128, blank=True)
    
    # Rollback information
    rollback_available = models.BooleanField(default=False)
    rollback_date = models.DateTimeField(null=True, blank=True)
    rollback_reason = models.TextField(blank=True)
    
    # Metadata
    metadata = models.JSONField(default=dict, blank=True)
    
    # Audit
    initiated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='initiated_recoveries'
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_portal_recovery_logs'
        indexes = [
            models.Index(fields=['recovery_type', 'status', 'initiated_at']),
            models.Index(fields=['source_backup', 'initiated_at']),
            models.Index(fields=['success', 'initiated_at']),
            models.Index(fields=['initiated_by', 'initiated_at']),
            models.Index(fields=['source_timestamp', 'recovery_type']),
        ]
        ordering = ['-initiated_at']
    
    def __str__(self):
        return f"{self.recovery_type}: {self.recovery_name} ({self.status})"
    
    def save(self, *args, **kwargs):
        # Auto-calculate duration if completed
        if self.completed_at and self.started_at and not self.duration_seconds:
            self.duration_seconds = int((self.completed_at - self.started_at).total_seconds())
        
        super().save(*args, **kwargs)
    
    @classmethod
    def initiate_recovery(cls, recovery_type, recovery_name, source_location, **kwargs):
        """Initiate a new recovery operation."""
        recovery = cls.objects.create(
            recovery_type=recovery_type,
            recovery_name=recovery_name,
            source_location=source_location,
            initiated_at=timezone.now(),
            metadata=kwargs
        )
        return recovery
    
    def start_recovery(self, target_database=None, target_tables=None, **kwargs):
        """Start the recovery process."""
        self.status = 'RUNNING'
        self.started_at = timezone.now()
        
        if target_database:
            self.target_database = target_database
        
        if target_tables:
            self.target_tables = target_tables
        
        if kwargs:
            self.metadata.update(kwargs)
        
        self.save()
    
    def complete_recovery(self, records_recovered=0, files_recovered=0, **kwargs):
        """Mark recovery as completed."""
        self.status = 'COMPLETED'
        self.success = True
        self.completed_at = timezone.now()
        self.records_recovered = records_recovered
        self.files_recovered = files_recovered
        
        if kwargs:
            self.metadata.update(kwargs)
        
        self.save()
    
    def fail_recovery(self, error_message, error_code=None, **kwargs):
        """Mark recovery as failed."""
        self.status = 'FAILED'
        self.success = False
        self.completed_at = timezone.now()
        self.error_message = error_message
        self.error_code = error_code
        
        if kwargs:
            self.metadata.update(kwargs)
        
        self.save()
    
    def verify_recovery(self, checksum):
        """Verify recovery integrity."""
        self.verified = True
        self.verification_date = timezone.now()
        self.verification_checksum = checksum
        self.save()
    
    def rollback_recovery(self, reason):
        """Rollback the recovery."""
        self.status = 'ROLLED_BACK'
        self.rollback_date = timezone.now()
        self.rollback_reason = reason
        self.save()
    
    @classmethod
    def get_recovery_statistics(cls, days=30):
        """Get recovery statistics for the last N days."""
        from django.utils import timezone
        from django.db.models import Count, Sum, Avg
        
        since = timezone.now() - timezone.timedelta(days=days)
        
        stats = cls.objects.filter(
            initiated_at__gte=since
        ).aggregate(
            total_recoveries=Count('id'),
            successful_recoveries=Count('id', filter=models.Q(success=True)),
            failed_recoveries=Count('id', filter=models.Q(success=False)),
            total_records_recovered=Sum('records_recovered'),
            avg_duration=Avg('duration_seconds'),
        )
        
        # Calculate success rate
        if stats['total_recoveries'] > 0:
            stats['success_rate'] = (stats['successful_recoveries'] / stats['total_recoveries']) * 100
        else:
            stats['success_rate'] = 0
        
        return stats
