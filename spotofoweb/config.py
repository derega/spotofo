
from django.conf import settings

CLIENT_SECRET = getattr(settings, 'SPOTOFO_CLIENT_SECRET', None)
CLIENT_ID = getattr(settings, 'SPOTOFO_CLIENT_ID', None)
REDIRECT_URI = getattr(settings, 'SPOTOFO_REDIRECT_URI', None)
INFLUX_WRITE_URL = getattr(settings, 'SPOTOFO_INFLUX_WRITE_URL', None)
AUTHKEYS = getattr(settings, 'SPOTOFO_AUTHKEYS', {})

