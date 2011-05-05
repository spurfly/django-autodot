from django.core.cache import get_cache
from autodot.conf import settings

cache = get_cache(settings.CACHE_BACKEND)
