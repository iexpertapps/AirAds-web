from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count, Sum, Avg
from .models import Vendor, Promotion, VendorReel, Tag, City, Area


@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    """
    Admin interface for Vendor model.
    """
    list_display = [
        'name',
        'category',
        'tier',
        'is_verified',
        'is_active',
        'popularity_score',
        'location_display',
        'created_at',
    ]
    list_filter = [
        'category',
        'tier',
        'is_verified',
        'is_active',
        'created_at',
    ]
    search_fields = [
        'name',
        'description',
        'address',
        'tags',
    ]
    readonly_fields = [
        'id',
        'popularity_score',
        'interaction_count',
        'created_at',
        'updated_at',
    ]
    ordering = ['-created_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'category', 'subcategory')
        }),
        ('Location', {
            'fields': ('location', 'address')
        }),
        ('Business Details', {
            'fields': (
                'tier',
                'is_verified',
                'is_active',
                'phone',
                'email',
                'website',
                'business_hours'
            )
        }),
        ('Media', {
            'fields': ('logo_url', 'cover_image_url')
        }),
        ('Tags & System', {
            'fields': ('tags', 'system_tags')
        }),
        ('Analytics', {
            'fields': ('popularity_score', 'interaction_count'),
            'classes': ('collapse',)
        }),
        ('System', {
            'fields': (
                'id',
                'created_at',
                'updated_at'
            ),
            'classes': ('collapse',)
        }),
    )
    
    def location_display(self, obj):
        """Display location coordinates."""
        if obj.lat and obj.lng:
            return format_html(
                '<span title="Click to view on map">{:.4f}, {:.4f}</span>',
                obj.lat,
                obj.lng
            )
        return "No location"
    location_display.short_description = 'Location'
    
    def get_queryset(self, request):
        """Optimize queries."""
        qs = super().get_queryset(request)
        return qs.select_related().prefetch_related('promotions', 'reels')


@admin.register(Promotion)
class PromotionAdmin(admin.ModelAdmin):
    """
    Admin interface for Promotion model.
    """
    list_display = [
        'title',
        'vendor_name',
        'discount_display',
        'is_flash_deal',
        'is_active',
        'start_time',
        'end_time',
        'usage_display',
    ]
    list_filter = [
        'discount_type',
        'is_flash_deal',
        'is_active',
        'start_time',
        'end_time',
    ]
    search_fields = [
        'title',
        'description',
        'vendor__name',
    ]
    readonly_fields = [
        'id',
        'usage_count',
        'created_at',
        'updated_at',
    ]
    ordering = ['-created_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('vendor', 'title', 'description')
        }),
        ('Discount Details', {
            'fields': (
                'discount_type',
                'discount_percent',
                'discount_amount'
            )
        }),
        ('Flash Deal Settings', {
            'fields': ('is_flash_deal', 'flash_duration_minutes')
        }),
        ('Timing', {
            'fields': ('start_time', 'end_time', 'is_active')
        }),
        ('Usage Limits', {
            'fields': ('usage_limit', 'usage_count')
        }),
        ('Media', {
            'fields': ('image_url',)
        }),
        ('System', {
            'fields': (
                'id',
                'created_at',
                'updated_at'
            ),
            'classes': ('collapse',)
        }),
    )
    
    def vendor_name(self, obj):
        """Display vendor name."""
        return obj.vendor.name
    vendor_name.short_description = 'Vendor'
    vendor_name.admin_order_field = 'vendor__name'
    
    def discount_display(self, obj):
        """Display discount information."""
        if obj.discount_type == 'PERCENTAGE':
            return f"{obj.discount_percent}%"
        elif obj.discount_type == 'FIXED':
            return f"${obj.discount_amount}"
        elif obj.discount_type == 'BOGO':
            return "Buy One Get One"
        elif obj.discount_type == 'FREE_ITEM':
            return "Free Item"
        return obj.discount_type
    discount_display.short_description = 'Discount'
    
    def usage_display(self, obj):
        """Display usage information."""
        if obj.usage_limit:
            return f"{obj.usage_count}/{obj.usage_limit}"
        return f"{obj.usage_count} (unlimited)"
    usage_display.short_description = 'Usage'
    
    def get_queryset(self, request):
        """Optimize queries."""
        qs = super().get_queryset(request)
        return qs.select_related('vendor')


@admin.register(VendorReel)
class VendorReelAdmin(admin.ModelAdmin):
    """
    Admin interface for VendorReel model.
    """
    list_display = [
        'title',
        'vendor_name',
        'duration_display',
        'view_count',
        'completion_rate_display',
        'cta_tap_rate_display',
        'is_active',
        'is_approved',
        'created_at',
    ]
    list_filter = [
        'is_active',
        'is_approved',
        'created_at',
    ]
    search_fields = [
        'title',
        'description',
        'vendor__name',
    ]
    readonly_fields = [
        'id',
        'view_count',
        'cta_tap_count',
        'completion_count',
        'created_at',
        'updated_at',
    ]
    ordering = ['-created_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('vendor', 'title', 'description')
        }),
        ('Media', {
            'fields': (
                'video_url',
                'thumbnail_url',
                'duration_seconds'
            )
        }),
        ('Call to Action', {
            'fields': ('cta_text', 'cta_url')
        }),
        ('Status', {
            'fields': ('is_active', 'is_approved')
        }),
        ('Analytics', {
            'fields': (
                'view_count',
                'cta_tap_count',
                'completion_count'
            ),
            'classes': ('collapse',)
        }),
        ('System', {
            'fields': (
                'id',
                'created_at',
                'updated_at'
            ),
            'classes': ('collapse',)
        }),
    )
    
    def vendor_name(self, obj):
        """Display vendor name."""
        return obj.vendor.name
    vendor_name.short_description = 'Vendor'
    vendor_name.admin_order_field = 'vendor__name'
    
    def duration_display(self, obj):
        """Display duration in minutes and seconds."""
        minutes = obj.duration_seconds // 60
        seconds = obj.duration_seconds % 60
        return f"{minutes}:{seconds:02d}"
    duration_display.short_description = 'Duration'
    
    def completion_rate_display(self, obj):
        """Display completion rate with color."""
        rate = obj.completion_rate
        if rate >= 80:
            color = 'green'
        elif rate >= 50:
            color = 'orange'
        else:
            color = 'red'
        return format_html(
            '<span style="color: {};">{:.1f}%</span>',
            color,
            rate
        )
    completion_rate_display.short_description = 'Completion Rate'
    
    def cta_tap_rate_display(self, obj):
        """Display CTA tap rate with color."""
        rate = obj.cta_tap_rate
        if rate >= 10:
            color = 'green'
        elif rate >= 5:
            color = 'orange'
        else:
            color = 'red'
        return format_html(
            '<span style="color: {};">{:.1f}%</span>',
            color,
            rate
        )
    cta_tap_rate_display.short_description = 'CTA Tap Rate'
    
    def get_queryset(self, request):
        """Optimize queries."""
        qs = super().get_queryset(request)
        return qs.select_related('vendor')


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    """
    Admin interface for Tag model.
    """
    list_display = [
        'name',
        'category',
        'vendor_count',
        'search_count',
        'color_display',
        'is_active',
        'sort_order',
    ]
    list_filter = [
        'category',
        'is_active',
        'created_at',
    ]
    search_fields = [
        'name',
        'slug',
        'description',
    ]
    readonly_fields = [
        'id',
        'vendor_count',
        'search_count',
        'created_at',
        'updated_at',
    ]
    ordering = ['category', 'sort_order', 'name']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'description')
        }),
        ('Appearance', {
            'fields': ('icon_url', 'color')
        }),
        ('Organization', {
            'fields': ('category', 'sort_order', 'is_active')
        }),
        ('Analytics', {
            'fields': ('vendor_count', 'search_count'),
            'classes': ('collapse',)
        }),
        ('System', {
            'fields': (
                'id',
                'created_at',
                'updated_at'
            ),
            'classes': ('collapse',)
        }),
    )
    
    def color_display(self, obj):
        """Display color with preview."""
        return format_html(
            '<span style="display: inline-block; width: 20px; height: 20px; '
            'background-color: {}; border: 1px solid #ccc; vertical-align: middle;"></span> '
            '{}',
            obj.color,
            obj.color
        )
    color_display.short_description = 'Color'
    
    actions = ['update_vendor_counts']
    
    def update_vendor_counts(self, request, queryset):
        """Update vendor counts for selected tags."""
        updated_count = 0
        for tag in queryset:
            tag.update_vendor_count()
            updated_count += 1
        
        self.message_user(request, f'Updated vendor counts for {updated_count} tags.')
    update_vendor_counts.short_description = 'Update vendor counts'


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    """
    Admin interface for City model.
    """
    list_display = [
        'name',
        'country',
        'vendor_count',
        'location_display',
        'is_active',
        'sort_order',
    ]
    list_filter = [
        'country',
        'is_active',
        'created_at',
    ]
    search_fields = [
        'name',
        'slug',
    ]
    readonly_fields = [
        'id',
        'vendor_count',
        'created_at',
        'updated_at',
    ]
    ordering = ['sort_order', 'name']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'country')
        }),
        ('Location', {
            'fields': ('location', 'bounds_north', 'bounds_south', 'bounds_east', 'bounds_west')
        }),
        ('Settings', {
            'fields': ('is_active', 'sort_order')
        }),
        ('Analytics', {
            'fields': ('vendor_count',),
            'classes': ('collapse',)
        }),
        ('System', {
            'fields': (
                'id',
                'created_at',
                'updated_at'
            ),
            'classes': ('collapse',)
        }),
    )
    
    def location_display(self, obj):
        """Display location coordinates."""
        if obj.lat and obj.lng:
            return format_html(
                '<span title="Click to view on map">{:.4f}, {:.4f}</span>',
                obj.lat,
                obj.lng
            )
        return "No location"
    location_display.short_description = 'Location'
    
    actions = ['update_vendor_counts']
    
    def update_vendor_counts(self, request, queryset):
        """Update vendor counts for selected cities."""
        updated_count = 0
        for city in queryset:
            city.update_vendor_count()
            updated_count += 1
        
        self.message_user(request, f'Updated vendor counts for {updated_count} cities.')
    update_vendor_counts.short_description = 'Update vendor counts'


@admin.register(Area)
class AreaAdmin(admin.ModelAdmin):
    """
    Admin interface for Area model.
    """
    list_display = [
        'name',
        'city_name',
        'vendor_count',
        'location_display',
        'is_active',
        'sort_order',
    ]
    list_filter = [
        'city',
        'is_active',
        'created_at',
    ]
    search_fields = [
        'name',
        'slug',
        'city__name',
    ]
    readonly_fields = [
        'id',
        'vendor_count',
        'created_at',
        'updated_at',
    ]
    ordering = ['city', 'sort_order', 'name']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('city', 'name', 'slug')
        }),
        ('Location', {
            'fields': ('location', 'bounds_north', 'bounds_south', 'bounds_east', 'bounds_west')
        }),
        ('Settings', {
            'fields': ('is_active', 'sort_order')
        }),
        ('Analytics', {
            'fields': ('vendor_count',),
            'classes': ('collapse',)
        }),
        ('System', {
            'fields': (
                'id',
                'created_at',
                'updated_at'
            ),
            'classes': ('collapse',)
        }),
    )
    
    def city_name(self, obj):
        """Display city name."""
        return obj.city.name
    city_name.short_description = 'City'
    city_name.admin_order_field = 'city__name'
    
    def location_display(self, obj):
        """Display location coordinates."""
        if obj.lat and obj.lng:
            return format_html(
                '<span title="Click to view on map">{:.4f}, {:.4f}</span>',
                obj.lat,
                obj.lng
            )
        return "No location"
    location_display.short_description = 'Location'
    
    actions = ['update_vendor_counts']
    
    def update_vendor_counts(self, request, queryset):
        """Update vendor counts for selected areas."""
        updated_count = 0
        for area in queryset:
            area.update_vendor_count()
            updated_count += 1
        
        self.message_user(request, f'Updated vendor counts for {updated_count} areas.')
    update_vendor_counts.short_description = 'Update vendor counts'


# Customize admin site headers
admin.site.site_header = 'AirAds User Portal Administration'
admin.site.site_title = 'AirAds Admin'
admin.site.index_title = 'Welcome to AirAds User Portal Admin'
