from .forms import LeadForm
from .models import SiteSettings


def site_data(request):
    # One shared site configuration is editable in /upravlenie/.
    return {
        "site": SiteSettings.objects.first(),
        "lead_form": LeadForm(),
    }
