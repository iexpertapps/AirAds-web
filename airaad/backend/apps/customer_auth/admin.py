from django.contrib import admin
from django.utils.html import format_html
from .models import CustomerUser, ConsentRecord, GuestToken


@admin.register(CustomerUser)
class CustomerUserAdmin(admin.ModelAdmin):
    """
    Admin interface for CustomerUser model.
    """
    list_display = [
        'email',
        'display_name',
        'created_at',
        'is_deleted',
        'deleted_at',
    ]
    list_filter = [
        'is_deleted',
        'created_at',
        'deleted_at',
    ]
    search_fields = [
        'user__email',
        'display_name',
    ]
    readonly_fields = [
        'id',
        'user',
        'created_at',
        'updated_at',
        'deleted_at',
        'data_export_requested_at',
    ]
    ordering = ['-created_at']
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'display_name', 'avatar_url', 'phone_number')
        }),
        ('Session & Social', {
            'fields': ('guest_token', 'social_auth_provider', 'social_auth_id')
        }),
        ('Privacy & Compliance', {
            'fields': (
                'behavioral_data',
                'data_export_requested_at',
                'consent_records'
            )
        }),
        ('System', {
            'fields': (
                'created_at',
                'updated_at',
                'is_deleted',
                'deleted_at'
            ),
            'classes': ('collapse',)
        }),
    )
    
    def email(self, obj):
        return obj.user.email
    email.short_description = 'Email'
    email.admin_order_field = 'user__email'
    
    def get_queryset(self, request):
        """Include soft-deleted records but mark them."""
        qs = super().get_queryset(request)
        return qs.select_related('user')
    
    actions = ['soft_delete_selected', 'restore_selected']
    
    def soft_delete_selected(self, request, queryset):
        """Soft delete selected customers."""
        count = queryset.count()
        for customer in queryset:
            customer.soft_delete()
        self.message_user(request, f'Soft deleted {count} customers.')
    soft_delete_selected.short_description = 'Soft delete selected customers'
    
    def restore_selected(self, request, queryset):
        """Restore soft-deleted customers."""
        count = queryset.filter(is_deleted=True).update(
            is_deleted=False,
            deleted_at=None
        )
        self.message_user(request, f'Restored {count} customers.')
    restore_selected.short_description = 'Restore selected customers'


@admin.register(ConsentRecord)
class ConsentRecordAdmin(admin.ModelAdmin):
    """
    Admin interface for ConsentRecord model.
    """
    list_display = [
        'get_identifier',
        'consent_type',
        'consented',
        'consent_version',
        'ip_address',
        'consented_at',
    ]
    list_filter = [
        'consent_type',
        'consented',
        'consent_version',
        'consented_at',
    ]
    search_fields = [
        'user__user__email',
        'guest_token',
        'ip_address',
        'user_agent',
    ]
    readonly_fields = [
        'id',
        'consented_at',
        'ip_address',
        'user_agent',
    ]
    ordering = ['-consented_at']
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'guest_token')
        }),
        ('Consent Details', {
            'fields': (
                'consent_type',
                'consented',
                'consent_version',
                'context'
            )
        }),
        ('Metadata', {
            'fields': (
                'ip_address',
                'user_agent',
                'consented_at'
            ),
            'classes': ('collapse',)
        }),
    )
    
    def get_identifier(self, obj):
        """Get user identifier for display."""
        if obj.user:
            email = obj.user.user.email
            return format_html(
                '<span title="Customer User">{}</span>',
                email
            )
        else:
            return format_html(
                '<span title="Guest Token">Guest: {}</span>',
                str(obj.guest_token)[:8] + '...'
            )
    get_identifier.short_description = 'User'
    get_identifier.admin_order_field = 'user__user__email'
    
    def get_queryset(self, request):
        """Optimize queries."""
        qs = super().get_queryset(request)
        return qs.select_related('user__user')


@admin.register(GuestToken)
class GuestTokenAdmin(admin.ModelAdmin):
    """
    Admin interface for GuestToken model.
    """
    list_display = [
        'token_short',
        'created_at',
        'expires_at',
        'is_active',
        'api_calls_count',
        'last_used_at',
        'is_expired_display',
    ]
    list_filter = [
        'is_active',
        'created_at',
        'expires_at',
    ]
    search_fields = [
        'token',
        'ip_address',
        'user_agent',
    ]
    readonly_fields = [
        'token',
        'created_at',
        'api_calls_count',
        'last_used_at',
    ]
    ordering = ['-created_at']
    
    fieldsets = (
        ('Token Information', {
            'fields': ('token', 'created_at', 'expires_at', 'is_active')
        }),
        ('Usage Statistics', {
            'fields': (
                'api_calls_count',
                'last_used_at'
            )
        }),
        ('Metadata', {
            'fields': ('ip_address', 'user_agent'),
            'classes': ('collapse',)
        }),
    )
    
    def token_short(self, obj):
        """Display shortened token."""
        return str(obj.token)[:8] + '...'
    token_short.short_description = 'Token'
    
    def is_expired_display(self, obj):
        """Display expiration status with color."""
        if obj.is_expired:
            return format_html(
                '<span style="color: red;">Expired</span>'
            )
        return format_html(
            '<span style="color: green;">Active</span>'
        )
    is_expired_display.short_description = 'Status'
    
    actions = ['deactivate_expired', 'cleanup_expired']
    
    def deactivate_expired(self, request, queryset):
        """Deactivate expired tokens."""
        from django.utils import timezone
        expired_tokens = queryset.filter(expires_at__lt=timezone.now())
        count = expired_tokens.update(is_active=False)
        self.message_user(request, f'Deactivated {count} expired tokens.')
    deactivate_expired.short_description = 'Deactivate expired tokens'
    
    def cleanup_expired(self, request, queryset):
        """Delete expired tokens (hard delete)."""
        from django.utils import timezone
        expired_tokens = queryset.filter(expires_at__lt=timezone.now())
        count = expired_tokens.count()
        expired_tokens.delete()
        self.message_user(request, f'Deleted {count} expired tokens.')
    cleanup_expired.short_description = 'Delete expired tokens'


# Customize admin site headers
admin.site.site_header = 'AirAds Customer Portal Administration'
admin.site.site_title = 'AirAds Admin'
admin.site.index_title = 'Welcome to AirAds Customer Portal Admin'
