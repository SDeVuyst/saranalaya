from django.urls import path, include
from django.utils.translation import gettext_lazy as _
from django.conf.urls.i18n import i18n_patterns
from . import views
from .sites import saranalaya_admin_site

urlpatterns = i18n_patterns(
    path('', views.index, name="index"),
    path(_('children/'), views.kinderen, name="children"),
    path(_('children/<int:id>/'), views.kind_detail, name="child_detail"),
    path(_('about-us/'), views.over_ons, name="about-us"),
    path(_('support-us/'), views.steun_ons, name="support-us"),
    path(_('news/'), views.nieuws, name="news"),
    path(_('news/<int:id>/'), views.nieuws_detail, name="news_detail"),
    path(_('contact/'), views.contact, name='contact'),

    path('admin/', saranalaya_admin_site.urls),    
    path('i18n/', include('django.conf.urls.i18n')),
)