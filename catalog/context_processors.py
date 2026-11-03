from .forms import LeadForm
from .models import PrivacyPolicy, SiteSettings


def site_data(request):
    # Один опубликованный документ используется обеими формами заявки.
    policy = PrivacyPolicy.current()
    return {
        "site": SiteSettings.objects.first(),
        "privacy_policy": policy,
        "lead_form": LeadForm(initial={"consent_version": policy.version} if policy else None),
    }
