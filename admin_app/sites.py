from unfold.sites import UnfoldAdminSite
from .forms import LoginForm

class SaranalayaAdminSite(UnfoldAdminSite):
    login_form = LoginForm


saranalaya_admin_site = SaranalayaAdminSite()