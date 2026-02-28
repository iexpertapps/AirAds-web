from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count, Sum, Avg
from .models import UserPreference, UserSearchHistory, UserVendorInteraction, FlashDealAlert, NearbyReelView


@admin.register(UserPreference)
class UserPreferenceAdmin(admin.ModelAdmin):
    """
    Admin interface for UserPreference model.
    """
    list_display = [
        'get_identifier',
        'default_view',
        'search_radius_m',
        'price_range',
        'theme',
        'notification_status',
        'updated_at',
    ]
    list_filter = [
        'default_view',
        'search_radius_m',
        'price_range',
        'theme',
        'notifications_nearby_deals',
        'notifications_flash_deals',
        'notifications_new_vendors',
        'auto_location_enabled',
        'updated_at',
    ]
    search_fields = [
        'user__user__email',
        'preferred_category_slugs',
        'manual_location_name',
    ]
    readonly_fields = [
        'id',
        'created_at',
        'updated_at',
    ]
    ordering = ['-updated_at']
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'guest_token')
        }),
        ('UI Preferences', {
            'fields': (
                'default_view',
                'search_radius_m',
                'show_open_now_only',
                'theme'
            )
        }),
        ('Content Preferences', {
            'fields': (
                'preferred_category_slugs',
                'price_range'
            )
        }),
        ('Notification Preferences', {
            'fields': (
                'notifications_nearby_deals',
                'notifications_flash_deals',
                'notifications_new_vendors',
                'notifications_all_off'
            )
        }),
        ('Location Preferences', {
            'fields': (
                'auto_location_enabled',
                'manual_location_lat',
                'manual_location_lng',
                'manual_location_name'
            )
        }),
        ('System', {
            'fields': (
                'created_at',
                'updated_at'
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
    
    def notification_status(self, obj):
        """Display notification status with color."""
        if obj.notifications_all_off:
            return format_html(
                '<span style="color: red;">All Off</span>'
            )
        enabled_count = sum([
            obj.notifications_nearby_deals,
            obj.notifications_flash_deals,
            obj.notifications_new_vendors
        ])
        if enabled_count == 3:
            return format_html(
                '<span style="color: green;">All On</span>'
            )
        return format_html(
            '<span style="color: orange;">{}/3 On</span>',
            enabled_count
        )
    notification_status.short_description = 'Notifications'
    
    def get_queryset(self, request):
        """Optimize queries."""
        qs = super().get_queryset(request)
        return qs.select_related('user__user')


@admin.register(UserSearchHistory)
class UserSearchHistoryAdmin(admin.ModelAdmin):
    """
    Admin interface for UserSearchHistory model.
    """
    list_display = [
        'get_identifier',
        'query_text',
        'query_type',
        'extracted_category',
        'result_count',
        'searched_at',
    ]
    list_filter = [
        'query_type',
        'extracted_category',
        'result_count',
        'searched_at',
    ]
    search_fields = [
        'query_text',
        'extracted_intent',
        'user__user__email',
    ]
    readonly_fields = [
        'id',
        'searched_at',
    ]
    ordering = ['-searched_at']
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'guest_token')
        }),
        ('Search Details', {
            'fields': (
                'query_text',
                'query_type',
                'extracted_category',
                'extracted_intent',
                'extracted_price_range'
            )
        }),
        ('Search Context', {
            'fields': (
                'search_lat',
                'search_lng',
                'search_radius_m',
                'result_count',
                'navigated_to_vendor_id'
            )
        }),
        ('System', {
            'fields': ('id', 'searched_at'),
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


@admin.register(UserVendorInteraction)
class UserVendorInteractionAdmin(admin.ModelAdmin):
    """
    Admin interface for UserVendorInteraction model.
    """
    list_display = [
        'get_identifier',
        'vendor_id',
        'interaction_type',
        'session_id_short',
        'interacted_at',
    ]
    list_filter = [
        'interaction_type',
        'interacted_at',
    ]
    search_fields = [
        'vendor_id',
        'user__user__email',
        'session_id',
    ]
    readonly_fields = [
        'id',
        'interacted_at',
    ]
    ordering = ['-interacted_at']
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'guest_token')
        }),
        ('Interaction Details', {
            'fields': (
                'vendor_id',
                'interaction_type',
                'session_id'
            )
        }),
        ('Location Context', {
            'fields': ('lat', 'lng')
        }),
        ('Additional Data', {
            'fields': ('metadata',)
        }),
        ('System', {
            'fields': ('id', 'interacted_at'),
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
    
    def session_id_short(self, obj):
        """Display shortened session ID."""
        return str(obj.session_id)[:8] + '...'
    session_id_short.short_description = 'Session ID'
    
    def get_queryset(self, request):
        """Optimize queries."""
        qs = super().get_queryset(request)
        return qs.select_related('user__user')


@admin.register(FlashDealAlert)
class FlashDealAlertAdmin(admin.ModelAdmin):
    """
    Admin interface for FlashDealAlert model.
    """
    list_display = [
        'get_identifier',
        'discount_id',
        'vendor_id',
        'alert_status',
        'alerted_at',
    ]
    list_filter = [
        'dismissed',
        'tapped',
        'alerted_at',
    ]
    search_fields = [
        'discount_id',
        'vendor_id',
        'user__user__email',
    ]
    readonly_fields = [
        'id',
        'alerted_at',
    ]
    ordering = ['-alerted_at']
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'guest_token')
        }),
        ('Deal Information', {
            'fields': ('discount_id', 'vendor_id')
        }),
        ('Alert Status', {
            'fields': (
                'dismissed',
                'dismissed_at',
                'tapped',
                'tapped_at'
            )
        }),
        ('System', {
            'fields': ('id', 'alerted_at'),
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
    
    def alert_status(self, obj):
        """Display alert status with color."""
        if obj.tapped:
            return format_html(
                '<span style="color: green;">Tapped</span>'
            )
        elif obj.dismissed:
            return format_html(
                '<span style="color: orange;">Dismissed</span>'
            )
        else:
            return format_html(
                '<span style="color: blue;">Active</span>'
            )
    alert_status.short_description = 'Status'
    
    def get_queryset(self, request):
        """Optimize queries."""
        qs = super().get_queryset(request)
        return qs.select_related('user__user')


@admin.register(NearbyReelView)
class NearbyReelViewAdmin(admin.ModelAdmin):
    """
    Admin interface for NearbyReelView model.
    """
    list_display = [
        'get_identifier',
        'reel_id',
        'vendor_id',
        'watched_seconds',
        'view_status',
        'viewed_at',
    ]
    list_filter = [
        'completed',
        'cta_tapped',
        'viewed_at',
    ]
    search_fields = [
        'reel_id',
        'vendor_id',
        'user__user__email',
    ]
    readonly_fields = [
        'id',
        'viewed_at',
    ]
    ordering = ['-viewed_at']
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'guest_token')
        }),
        ('Reel Information', {
            'fields': ('reel_id', 'vendor_id')
        }),
        ('View Metrics', {
            'fields': (
                'watched_seconds',
                'completed',
                'cta_tapped'
            )
        }),
        ('Location Context', {
            'fields': ('lat', 'lng')
        }),
        ('System', {
            'fields': ('id', 'viewed_at'),
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
    
    def view_status(self, obj):
        """Display view status with color."""
        if obj.cta_tapped:
            return format_html(
                '<span style="color: green;">CTA Tapped</span>'
            )
        elif obj.completed:
            return format_html(
                '<span style="color: blue;">Completed</span>'
            )
        else:
            return format_html(
                '<span style="color: orange;">Partial ({})</span>',
                obj.watched_seconds
            )
    view_status.short_description = 'Status'
    
    def get_queryset(self, request):
        """Optimize queries."""
        qs = super().get_queryset(request)
        return qs.select_related('user__user')


# Customize admin site headers
admin.site.site_header = 'AirAds User Preferences Administration'
admin.site.site_title = 'AirAds Admin'
admin.site.index_title = 'Welcome to AirAds User Preferences Admin'
