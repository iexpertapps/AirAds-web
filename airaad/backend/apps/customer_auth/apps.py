from django.apps import AppConfig


class CustomerAuthConfig(AppConfig):
    """
    Django app configuration for Customer Authentication.
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.customer_auth'
    verbose_name = 'Customer Authentication'
    
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
