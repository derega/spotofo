
import logging
from django.core.cache import cache
from django import forms
from django.http import HttpResponseRedirect
from django.contrib.auth.models import User
from django.contrib.auth import login as auth_login
from django.views.generic import View, FormView, TemplateView
import spotofo
from spotofoweb.models import SpotifyUser, Device, Playlist

LOG = logging.getLogger(__name__)


# These functions do the user management.
# They assume Django user and Spotify User are one and the same.
# Matching is done with "username".

def get_spotify_user(request):
  try:
    sp_user = SpotifyUser.objects.get(pk=request.session.get('spotify_user_id', None))
  except SpotifyUser.DoesNotExist:
    LOG.error('SPOTIFY USER DOES NOT EXIST')
    sp_user = request.user.spotify.all()[0]
  return sp_user


def login(request, sp_user):
  user = get_django_user(sp_user)
  user.backend = 'django.contrib.auth.backends.ModelBackend'
  auth_login(request, user)
  request.session['spotify_user_id'] = sp_user.pk


def get_django_user(sp_user):
  if not sp_user.user:
    user, created = User.objects.get_or_create(username=sp_user.username)
    if created:
      sp_user.user = user
      sp_user.save()
  return sp_user.user


# Views


class CurrentlyPlayingView(TemplateView):
  template_name = 'spotofoweb/currently_playing.html'

  def get_context_data(self, **kwargs):
    context = super(TemplateView, self).get_context_data(**kwargs)
    users = spotofo.get_users()
    cp = list(spotofo.get_currently_playing_trackinfo(users))
    context['currently_playing'] = cp
    context['playlists'] = Playlist.objects.all()
    return context


class DeviceSelectForm(forms.Form):
  devices = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple)


class DeviceSelectView(FormView):
  template_name = 'spotofoweb/device_selection.html'
  form_class = DeviceSelectForm
  active_devices = []

  def form_valid(self, form):
    devices = form.cleaned_data['devices']
    spuser = get_spotify_user(self.request)
    for d in spotofo.get_user_devices(spuser.username):
      if d['id'] in devices:
        spotofo.add_user_device(spuser.username, d)
    self.success_url = '/devices'
    return super(FormView, self).form_valid(form)

  def get_form(self, form_class=None):
    self.active_devices = Device.objects.filter(users__user__in=[self.request.user])
    form = super(FormView, self).get_form(form_class=None)
    choices = []
    for d in spotofo.get_user_devices(self.request.user.username):
      if d['id'] not in [ad.spid for ad in self.active_devices]:
        choices.append((str(d['id']), d['name']))
    form.fields['devices'].choices = choices
    return form

  def get_context_data(self, **kwargs):
    context = super(FormView, self).get_context_data(**kwargs)
    context['active_devices'] = self.active_devices
    context['spotifyuser'] = get_spotify_user(self.request)
    return context


class UsernameForm(forms.Form):
  username = forms.CharField(label='username', max_length=2048)


class AuthorizeUserView(FormView):
  template_name = 'spotofoweb/begin_authorize_user.html'
  form_class = UsernameForm

  def form_valid(self, form):
    username = form.cleaned_data['username']
    sp_oauth = spotofo.oauth_client()
    self.request.session['authorize_username'] = username
    url = sp_oauth.get_authorize_url(state=username)
    self.success_url = url
    return super(FormView, self).form_valid(form)


class AuthorizeResponseView(View):
  """Use Spotify to authorize Django session, e.g. login.
  """
  def get(self, request, *args, **kwargs):
    code = request.GET.get('code', None)
    state_username = request.GET.get('state', None)
    authorize_username = request.session.pop('authorize_username', None)
    if authorize_username and authorize_username == state_username:
      sp_oauth = spotofo.oauth_client()
      token_info = sp_oauth.get_access_token(code)
      if token_info:
        # Register new user, or get existing user for token_info
        sp_user = spotofo.save_token_info(authorize_username, token_info)
        login(request, sp_user)
        # TODO Remove this when playlist management has been implemented
        for pl in Playlist.objects.all():
          sp_user.playlists.add(pl)
    return HttpResponseRedirect('/')

