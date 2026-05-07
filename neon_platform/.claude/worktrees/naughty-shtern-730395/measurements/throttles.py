from rest_framework.throttling import SimpleRateThrottle


class TierBasedThrottle(SimpleRateThrottle):
    """
    Dynamic throttle that reads the user's tier and applies the matching rate.
    Rates are defined in settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"].
    """
    scope = "free_tier"  # default fallback

    def get_cache_key(self, request, view):
        if not request.user or not request.user.is_authenticated:
            self.scope = "anon"
            return self.cache_format % {
                "scope": self.scope,
                "ident": self.get_ident(request),
            }

        tier = getattr(request.user, "tier", "free")
        self.scope = f"{tier}_tier"
        return self.cache_format % {
            "scope": self.scope,
            "ident": str(request.user.pk),
        }

    def get_rate(self):
        from django.conf import settings
        rates = settings.REST_FRAMEWORK.get("DEFAULT_THROTTLE_RATES", {})
        return rates.get(self.scope, "10/day")
