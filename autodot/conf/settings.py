from django.core.exceptions import ImproperlyConfigured
from django.conf import settings

MEDIA_URL = getattr(settings, 'COMPRESS_URL', settings.MEDIA_URL)
if not MEDIA_URL.endswith('/'):
    raise ImproperlyConfigured(
        'The MEDIA_URL and COMPRESS_URL settings must have a trailing slash.')

MEDIA_ROOT = getattr(settings, 'COMPRESS_ROOT', settings.MEDIA_ROOT)
OUTPUT_DIR = getattr(settings, 'COMPRESS_OUTPUT_DIR', 'CACHE')
STORAGE = getattr(settings, 'COMPRESS_STORAGE', 'compressor.storage.CompressorFileStorage')

# rebuilds the cache every 30 days if nothing has changed.
REBUILD_TIMEOUT = getattr(settings, 'COMPRESS_REBUILD_TIMEOUT', 2592000) # 30 days

# the upper bound on how long any compression should take to be generated
# (used against dog piling, should be a lot smaller than REBUILD_TIMEOUT
MINT_DELAY = getattr(settings, 'COMPRESS_MINT_DELAY', 30) # 30 seconds

# check for file changes only after a delay (in seconds, disabled by default)
MTIME_DELAY = getattr(settings, 'COMPRESS_MTIME_DELAY', None)

# Allows changing verbosity from the settings.
VERBOSE = getattr(settings, "COMPRESS_VERBOSE", False)

# the cache backend to use
CACHE_BACKEND = getattr(settings, 'COMPRESS_CACHE_BACKEND', None)
if CACHE_BACKEND is None:
    # If we are on Django 1.3 AND using the new CACHES setting...
    if getattr(settings, "CACHES", None):
        CACHE_BACKEND = "default"
    else:
        # fallback for people still using the old CACHE_BACKEND setting
        CACHE_BACKEND = settings.CACHE_BACKEND
