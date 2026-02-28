#!/bin/bash
# AirAds Backup System - Production Backup Script
# This script runs automated backups for the AirAds User Portal
# Usage: ./run_backup.sh [backup_type]

set -e  # Exit on any error

# Configuration
BACKUP_DIR="/tmp/airad_backups"
LOG_DIR="/var/log/airad"
PYTHON_PATH="/Users/syedsmacbook/Developer/AirAds-web/airaad/backend"
BACKUP_SCRIPT="/Users/syedsmacbook/Developer/AirAds-web/scripts/backup_system.py"

# Create directories
mkdir -p "$BACKUP_DIR"
mkdir -p "$LOG_DIR"

# Logging
LOG_FILE="$LOG_DIR/backup_$(date +%Y%m%d_%H%M%S).log"
exec > >(tee -a "$LOG_FILE")
exec 2>&1

echo "=========================================="
echo "AirAds Backup System - $(date)"
echo "=========================================="

# Get backup type from argument or default to 'full'
BACKUP_TYPE=${1:-full}

echo "Starting backup type: $BACKUP_TYPE"

# Change to backend directory
cd "$PYTHON_PATH"

# Set Python path and run backup
export PYTHONPATH="$PYTHON_PATH:$PYTHON_PATH/.."
export DJANGO_SETTINGS_MODULE="config.settings.production"

# Run the backup script
python3 "$BACKUP_SCRIPT" --type "$BACKUP_TYPE"

# Check exit code
if [ $? -eq 0 ]; then
    echo "Backup completed successfully"
    
    # Clean up old log files (keep last 7 days)
    find "$LOG_DIR" -name "backup_*.log" -mtime +7 -delete
    
    # Clean up old backup files (keep last 24 hours)
    find "$BACKUP_DIR" -name "*.gz" -mtime +1 -delete
    find "$BACKUP_DIR" -name "*.sql" -mtime +1 -delete
    find "$BACKUP_DIR" -name "*.rdb" -mtime +1 -delete
    find "$BACKUP_DIR" -name "*.tar" -mtime +1 -delete
    
    echo "Cleanup completed"
else
    echo "Backup failed with exit code $?"
    exit 1
fi

echo "=========================================="
echo "Backup process finished - $(date)"
echo "=========================================="
