from django.apps import AppConfig


class UserPortalConfig(AppConfig):
    """
    Django app configuration for User Portal.
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.user_portal'
    verbose_name = 'User Portal'
    
    def ready(self):
        """
        App initialization.
        Import signals and register tasks.
        """
        # Import signals
        try:
            from . import signals
        except ImportError:
            # Signals file doesn't exist yet
            pass
        
        # Register Celery tasks
        try:
            from . import tasks
        except ImportError:
            # Tasks file doesn't exist yet
            pass
