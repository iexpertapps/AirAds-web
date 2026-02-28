from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from .models import GuestToken, CustomerUser


@shared_task(name='customer_auth.purge_expired_guest_tokens')
def purge_expired_guest_tokens():
    """
    Purge expired guest tokens older than 30 days.
    Runs daily at 3:00 AM.
    """
    cutoff_date = timezone.now() - timedelta(days=30)
    
    # Soft delete expired tokens
    expired_count = GuestToken.objects.filter(
        expires_at__lt=cutoff_date,
        is_active=True
    ).update(is_active=False)
    
    # Hard delete tokens expired for more than 60 days
    hard_delete_cutoff = timezone.now() - timedelta(days=60)
    hard_deleted_count = GuestToken.objects.filter(
        expires_at__lt=hard_delete_cutoff
    ).delete()[0]
    
    return {
        'soft_deleted': expired_count,
        'hard_deleted': hard_deleted_count,
        'message': f'Purged {expired_count} expired guest tokens (soft deleted) and {hard_deleted_count} tokens (hard deleted)'
    }


@shared_task(name='customer_auth.schedule_user_data_purge')
def schedule_user_data_purge(customer_user_id):
    """
    Schedule hard deletion of customer data after 30-day grace period.
    This task is scheduled when a user requests account deletion.
    """
    try:
        customer_user = CustomerUser.objects.get(id=customer_user_id)
        
        # Check if 30 days have passed since soft delete
        if customer_user.deleted_at:
            grace_period_end = customer_user.deleted_at + timedelta(days=30)
            
            if timezone.now() >= grace_period_end:
                # Hard delete the user and all related data
                user = customer_user.user
                
                # Delete related records (will be cascaded)
                customer_user.delete()
                user.delete()
                
                return {
                    'customer_user_id': customer_user_id,
                    'status': 'completed',
                    'message': f'Customer user {customer_user_id} permanently deleted after grace period'
                }
            else:
                # Reschedule for later
                remaining_days = (grace_period_end - timezone.now()).days
                schedule_user_data_purge.apply_async(
                    eta=grace_period_end,
                    kwargs={'customer_user_id': customer_user_id}
                )
                
                return {
                    'customer_user_id': customer_user_id,
                    'status': 'rescheduled',
                    'remaining_days': remaining_days,
                    'message': f'Deletion rescheduled for {remaining_days} days from now'
                }
        else:
            return {
                'customer_user_id': customer_user_id,
                'status': 'error',
                'message': 'Customer user was not soft deleted'
            }
            
    except CustomerUser.DoesNotExist:
        return {
            'customer_user_id': customer_user_id,
            'status': 'error',
            'message': 'Customer user not found'
        }


@shared_task(name='customer_auth.cleanup_old_consent_records')
def cleanup_old_consent_records():
    """
    Clean up old consent records (keep for 2 years).
    Runs monthly.
    """
    cutoff_date = timezone.now() - timedelta(days=730)  # 2 years
    
    deleted_count = 0
    
    # Delete consent records older than 2 years
    from .models import ConsentRecord
    deleted_count = ConsentRecord.objects.filter(
        consented_at__lt=cutoff_date
    ).delete()[0]
    
    return {
        'deleted_count': deleted_count,
        'message': f'Cleaned up {deleted_count} old consent records'
    }


@shared_task(name='customer_auth.update_guest_token_usage_stats')
def update_guest_token_usage_stats():
    """
    Update guest token usage statistics for monitoring.
    Runs hourly.
    """
    now = timezone.now()
    
    # Active guest tokens
    active_tokens = GuestToken.objects.filter(
        is_active=True,
        expires_at__gt=now
    ).count()
    
    # Tokens expiring in next 24 hours
    expiring_soon = GuestToken.objects.filter(
        is_active=True,
        expires_at__lte=now + timedelta(hours=24),
        expires_at__gt=now
    ).count()
    
    # Expired tokens (still marked as active)
    expired_but_active = GuestToken.objects.filter(
        is_active=True,
        expires_at__lt=now
    ).count()
    
    # Tokens created in last 24 hours
    recent_tokens = GuestToken.objects.filter(
        created_at__gte=now - timedelta(hours=24)
    ).count()
    
    stats = {
        'active_tokens': active_tokens,
        'expiring_soon': expiring_soon,
        'expired_but_active': expired_but_active,
        'recent_tokens': recent_tokens,
        'timestamp': now.isoformat(),
    }
    
    # Store stats in cache for monitoring
    from django.core.cache import cache
    cache.set('guest_token_stats', stats, timeout=3600)  # 1 hour
    
    return stats


@shared_task(name='customer_auth.send_account_deletion_reminders')
def send_account_deletion_reminders():
    """
    Send reminders to users about pending account deletion.
    Runs daily.
    """
    from django.core.mail import send_mail
    from django.conf import settings
    
    # Find users scheduled for deletion in next 7 days
    seven_days_from_now = timezone.now() + timedelta(days=7)
    
    users_to_remind = CustomerUser.objects.filter(
        is_deleted=True,
        deleted_at__lte=seven_days_from_now - timedelta(days=23),  # 23-30 days ago
        deleted_at__gte=seven_days_from_now - timedelta(days=30)   # exactly 30 days ago
    ).select_related('user')
    
    reminders_sent = 0
    
    for customer_user in users_to_remind:
        days_until_deletion = 30 - (timezone.now() - customer_user.deleted_at).days
        
        try:
            send_mail(
                subject=f'Account Deletion Reminder - {days_until_deletion} days remaining',
                message=f'''
                Dear {customer_user.display_name or customer_user.user.email},
                
                This is a reminder that your AirAds account deletion is scheduled in {days_until_deletion} days.
                
                After this date, all your personal data will be permanently deleted and cannot be recovered.
                
                If you changed your mind and want to keep your account, please contact our support team immediately.
                
                Best regards,
                AirAds Team
                ''',
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@airad.pk'),
                recipient_list=[customer_user.user.email],
                fail_silently=False,
            )
            
            reminders_sent += 1
            
        except Exception as e:
            # Log error but continue with other users
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to send deletion reminder to {customer_user.user.email}: {e}")
    
    return {
        'reminders_sent': reminders_sent,
        'message': f'Sent {reminders_sent} account deletion reminders'
    }
