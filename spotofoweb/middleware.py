
import logging
from django.contrib.auth import login as auth_login
from django.contrib.auth.models import User
from spotofoweb.models import AuthKey

LOG = logging.getLogger(__name__)


class AuthkeyMiddleware(object):
  def __init__(self, get_response):
    self.get_response = get_response

  def __call__(self, request):
    authkey = request.GET.get('auth', None)
    if authkey:
      try:
        ak = AuthKey.objects.get(authkey=authkey)
        user = ak.user
        user.backend = 'django.contrib.auth.backends.ModelBackend'
        auth_login(request, user)
      except AuthKey.DoesNotExist:
        LOG.error('AUTHKEYS user objects does not exist')
    response = self.get_response(request)
    return response

