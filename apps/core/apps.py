from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'id'
    name = 'apps.core'
    verbose_name = 'Core'
    
    def ready(self):
        """Run setup when Django app is ready"""
        # Import here to avoid circular imports
        from harakacare.settings.production import setup_production_data
        
        # Run setup with error handling
        try:
            setup_production_data()
        except Exception as e:
            # Don't crash the app on setup error
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Core app setup error: {str(e)}")
