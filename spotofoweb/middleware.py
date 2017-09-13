
from django.contrib.auth import login as auth_login
from django.contrib.auth.models import User
from spotofoweb.config import AUTHKEYS

class AuthkeyMiddleware(object):
  def __init__(self, get_response):
    self.get_response = get_response

  def __call__(self, request):
    authkey = request.GET.get('auth', None)
    if authkey in AUTHKEYS:
      try:
        user = User.objects.get(pk=AUTHKEYS[authkey])
        user.backend = 'django.contrib.auth.backends.ModelBackend'
        auth_login(request, user)
      except:
        print "ERROR"
    response = self.get_response(request)
    return response

