from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

class AdminAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'admin_app'
    verbose_name = _("Saranalaya Admin")
