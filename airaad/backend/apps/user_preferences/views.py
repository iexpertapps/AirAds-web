from django.http import JsonResponse
from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination

from .models import UserPreference, UserSearchHistory
from .services import (
    UserPreferenceService,
    SearchHistoryService,
    InteractionService,
    FlashDealService,
    ReelViewService,
    MigrationService,
)
from .serializers import (
    UserPreferenceSerializer,
    UserPreferenceUpdateSerializer,
    SearchHistorySerializer,
)
from common.responses import success_response, error_response
from common.permissions import IsCustomerUser, IsGuestOrAuthenticated


class UserPreferenceView(APIView):
    """
    Get or update user preferences.
    """
    permission_classes = [IsGuestOrAuthenticated]
    
    def get(self, request):
        """Get user preferences"""
        try:
            # Determine if user is authenticated or guest
            if request.user.is_authenticated:
                user_or_guest = request.user
            else:
                guest_token = request.headers.get('X-Guest-Token')
                if not guest_token:
                    return error_response(
                        message="Guest token required",
                        status_code=status.HTTP_400_BAD_REQUEST
                    )
                user_or_guest = guest_token
            
            preferences = UserPreferenceService.get_preferences(user_or_guest)
            if not preferences:
                return error_response(
                    message="Preferences not found",
                    status_code=status.HTTP_404_NOT_FOUND
                )
            
            return success_response(
                data=preferences,
                message="Preferences retrieved successfully",
                status_code=status.HTTP_200_OK
            )
            
        except Exception as e:
            return error_response(
                message="Failed to retrieve preferences",
                details=str(e),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def put(self, request):
        """Update user preferences"""
        serializer = UserPreferenceUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(
                message="Validation failed",
                details=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Determine if user is authenticated or guest
            if request.user.is_authenticated:
                user_or_guest = request.user
            else:
                guest_token = request.headers.get('X-Guest-Token')
                if not guest_token:
                    return error_response(
                        message="Guest token required",
                        status_code=status.HTTP_400_BAD_REQUEST
                    )
                user_or_guest = guest_token
            
            updated_preferences = UserPreferenceService.update_preferences(
                user_or_guest,
                serializer.validated_data
            )
            
            return success_response(
                data=updated_preferences,
                message="Preferences updated successfully",
                status_code=status.HTTP_200_OK
            )
            
        except Exception as e:
            return error_response(
                message="Failed to update preferences",
                details=str(e),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class SearchHistoryView(APIView):
    """
    Get or clear user search history.
    """
    permission_classes = [IsGuestOrAuthenticated]
    
    def get(self, request):
        """Get search history"""
        try:
            # Pagination
            paginator = PageNumberPagination()
            paginator.page_size = 20
            paginator.page_size_query_param = 'page_size'
            paginator.max_page_size = 50
            
            # Determine if user is authenticated or guest
            if request.user.is_authenticated:
                user_or_guest = request.user
            else:
                guest_token = request.headers.get('X-Guest-Token')
                if not guest_token:
                    return error_response(
                        message="Guest token required",
                        status_code=status.HTTP_400_BAD_REQUEST
                    )
                user_or_guest = guest_token
            
            # Get search history
            history_data = SearchHistoryService.get_search_history(user_or_guest, limit=100)
            
            # Paginate results
            paginated_history = paginator.paginate_queryset(history_data)
            
            return success_response(
                data={
                    'results': paginated_history,
                    'count': len(history_data),
                    'next': paginator.get_next_link(),
                    'previous': paginator.get_previous_link(),
                },
                message="Search history retrieved successfully",
                status_code=status.HTTP_200_OK
            )
            
        except Exception as e:
            return error_response(
                message="Failed to retrieve search history",
                details=str(e),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def delete(self, request):
        """Clear search history"""
        try:
            # Determine if user is authenticated or guest
            if request.user.is_authenticated:
                user_or_guest = request.user
            else:
                guest_token = request.headers.get('X-Guest-Token')
                if not guest_token:
                    return error_response(
                        message="Guest token required",
                        status_code=status.HTTP_400_BAD_REQUEST
                    )
                user_or_guest = guest_token
            
            deleted_count = SearchHistoryService.clear_search_history(user_or_guest)
            
            return success_response(
                data={'deleted_count': deleted_count},
                message="Search history cleared successfully",
                status_code=status.HTTP_200_OK
            )
            
        except Exception as e:
            return error_response(
                message="Failed to clear search history",
                details=str(e),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class InteractionTrackingView(APIView):
    """
    Track user-vendor interactions.
    """
    permission_classes = [IsGuestOrAuthenticated]
    
    def post(self, request):
        """Record vendor interaction"""
        try:
            vendor_id = request.data.get('vendor_id')
            interaction_type = request.data.get('interaction_type')
            session_id = request.data.get('session_id')
            lat = request.data.get('lat')
            lng = request.data.get('lng')
            metadata = request.data.get('metadata', {})
            
            if not vendor_id or not interaction_type:
                return error_response(
                    message="vendor_id and interaction_type are required",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            # Determine if user is authenticated or guest
            if request.user.is_authenticated:
                user_or_guest = request.user
            else:
                guest_token = request.headers.get('X-Guest-Token')
                if not guest_token:
                    return error_response(
                        message="Guest token required",
                        status_code=status.HTTP_400_BAD_REQUEST
                    )
                user_or_guest = guest_token
            
            # Record interaction
            interaction = InteractionService.record_interaction(
                user_or_guest=user_or_guest,
                vendor_id=vendor_id,
                interaction_type=interaction_type,
                session_id=session_id,
                lat=lat,
                lng=lng,
                **metadata
            )
            
            return success_response(
                data={'interaction_id': str(interaction.id)},
                message="Interaction recorded successfully",
                status_code=status.HTTP_201_CREATED
            )
            
        except Exception as e:
            return error_response(
                message="Failed to record interaction",
                details=str(e),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ReelViewTrackingView(APIView):
    """
    Track reel views.
    """
    permission_classes = [IsGuestOrAuthenticated]
    
    def post(self, request):
        """Record reel view"""
        try:
            reel_id = request.data.get('reel_id')
            vendor_id = request.data.get('vendor_id')
            watched_seconds = request.data.get('watched_seconds', 0)
            completed = request.data.get('completed', False)
            cta_tapped = request.data.get('cta_tapped', False)
            lat = request.data.get('lat')
            lng = request.data.get('lng')
            
            if not reel_id or not vendor_id:
                return error_response(
                    message="reel_id and vendor_id are required",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            # Determine if user is authenticated or guest
            if request.user.is_authenticated:
                user_or_guest = request.user
            else:
                guest_token = request.headers.get('X-Guest-Token')
                if not guest_token:
                    return error_response(
                        message="Guest token required",
                        status_code=status.HTTP_400_BAD_REQUEST
                    )
                user_or_guest = guest_token
            
            # Record reel view
            reel_view = ReelViewService.record_view(
                user_or_guest=user_or_guest,
                reel_id=reel_id,
                vendor_id=vendor_id,
                watched_seconds=watched_seconds,
                completed=completed,
                cta_tapped=cta_tapped,
                lat=lat,
                lng=lng
            )
            
            return success_response(
                data={'reel_view_id': str(reel_view.id)},
                message="Reel view recorded successfully",
                status_code=status.HTTP_201_CREATED
            )
            
        except Exception as e:
            return error_response(
                message="Failed to record reel view",
                details=str(e),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class FlashDealAlertView(APIView):
    """
    Manage flash deal alerts.
    """
    permission_classes = [IsGuestOrAuthenticated]
    
    def post(self, request):
        """Create flash deal alert"""
        try:
            discount_id = request.data.get('discount_id')
            vendor_id = request.data.get('vendor_id')
            
            if not discount_id or not vendor_id:
                return error_response(
                    message="discount_id and vendor_id are required",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            # Determine if user is authenticated or guest
            if request.user.is_authenticated:
                user_or_guest = request.user
            else:
                guest_token = request.headers.get('X-Guest-Token')
                if not guest_token:
                    return error_response(
                        message="Guest token required",
                        status_code=status.HTTP_400_BAD_REQUEST
                    )
                user_or_guest = guest_token
            
            # Check if alert should be created
            if not FlashDealService.should_alert(user_or_guest, discount_id, vendor_id):
                return success_response(
                    data={'alert_created': False},
                    message="Alert already exists for this deal",
                    status_code=status.HTTP_200_OK
                )
            
            # Create alert
            alert = FlashDealService.create_alert(user_or_guest, discount_id, vendor_id)
            
            return success_response(
                data={
                    'alert_created': True,
                    'alert_id': str(alert.id),
                },
                message="Flash deal alert created successfully",
                status_code=status.HTTP_201_CREATED
            )
            
        except Exception as e:
            return error_response(
                message="Failed to create flash deal alert",
                details=str(e),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def patch(self, request):
        """Update flash deal alert (dismiss or tap)"""
        try:
            discount_id = request.data.get('discount_id')
            action = request.data.get('action')  # 'dismiss' or 'tap'
            
            if not discount_id or not action:
                return error_response(
                    message="discount_id and action are required",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            # Determine if user is authenticated or guest
            if request.user.is_authenticated:
                user_or_guest = request.user
            else:
                guest_token = request.headers.get('X-Guest-Token')
                if not guest_token:
                    return error_response(
                        message="Guest token required",
                        status_code=status.HTTP_400_BAD_REQUEST
                    )
                user_or_guest = guest_token
            
            # Perform action
            if action == 'dismiss':
                success = FlashDealService.dismiss_alert(user_or_guest, discount_id)
                message = "Flash deal alert dismissed"
            elif action == 'tap':
                success = FlashDealService.tap_alert(user_or_guest, discount_id)
                message = "Flash deal alert tap recorded"
            else:
                return error_response(
                    message="Invalid action. Use 'dismiss' or 'tap'",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            if not success:
                return error_response(
                    message="Alert not found or already processed",
                    status_code=status.HTTP_404_NOT_FOUND
                )
            
            return success_response(
                data={'action_performed': action},
                message=message,
                status_code=status.HTTP_200_OK
            )
            
        except Exception as e:
            return error_response(
                message="Failed to update flash deal alert",
                details=str(e),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class MigrationView(APIView):
    """
    Migrate guest data to user account (internal use during login).
    """
    permission_classes = [permissions.IsAuthenticated]  # Only authenticated users can migrate
    
    def post(self, request):
        """Migrate guest data to user account"""
        try:
            guest_token = request.data.get('guest_token')
            if not guest_token:
                return error_response(
                    message="guest_token is required",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            customer_user = request.user.customer_profile
            
            # Perform migration
            migration_results = MigrationService.migrate_all_guest_data(
                guest_token, customer_user
            )
            
            return success_response(
                data=migration_results,
                message="Guest data migration completed successfully",
                status_code=status.HTTP_200_OK
            )
            
        except Exception as e:
            return error_response(
                message="Failed to migrate guest data",
                details=str(e),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UserStatsView(APIView):
    """
    Get user statistics and analytics.
    """
    permission_classes = [IsGuestOrAuthenticated]
    
    def get(self, request):
        """Get user statistics"""
        try:
            # Determine if user is authenticated or guest
            if request.user.is_authenticated:
                user_or_guest = request.user
            else:
                guest_token = request.headers.get('X-Guest-Token')
                if not guest_token:
                    return error_response(
                        message="Guest token required",
                        status_code=status.HTTP_400_BAD_REQUEST
                    )
                user_or_guest = guest_token
            
            # Get interaction stats
            interaction_stats = {
                'total_interactions': InteractionService.get_interaction_count(user_or_guest),
                'profile_views': InteractionService.get_interaction_count(user_or_guest, 'VIEW'),
                'navigation_clicks': InteractionService.get_interaction_count(user_or_guest, 'NAVIGATION'),
                'ar_taps': InteractionService.get_interaction_count(user_or_guest, 'TAP'),
            }
            
            # Get reel view stats
            reel_stats = ReelViewService.get_view_stats(user_or_guest)
            
            # Get search history count
            search_history_count = len(SearchHistoryService.get_search_history(user_or_guest, limit=1000))
            
            stats_data = {
                'interactions': interaction_stats,
                'reel_views': reel_stats,
                'search_history_count': search_history_count,
                'generated_at': timezone.now().isoformat(),
            }
            
            return success_response(
                data=stats_data,
                message="User statistics retrieved successfully",
                status_code=status.HTTP_200_OK
            )
            
        except Exception as e:
            return error_response(
                message="Failed to retrieve user statistics",
                details=str(e),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
