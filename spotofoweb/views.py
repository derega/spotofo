
from django.core.cache import cache
from django import forms
from django.http import HttpResponseRedirect
from django.contrib.auth.models import User
from django.contrib.auth import login as auth_login
from django.views.generic import View, FormView, TemplateView
import spotofo
from spotofoweb.models import Playlist


class CurrentlyPlayingView(TemplateView):
  template_name = 'spotofoweb/currently_playing.html'

  def get_context_data(self, **kwargs):
    context = super(TemplateView, self).get_context_data(**kwargs)
    users = spotofo.get_users()
    cp = list(spotofo.get_currently_playing_trackinfo(users))
    context['currently_playing'] = cp
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
  def get(self, request, *args, **kwargs):
    code = request.GET.get('code', None)
    username = request.GET.get('state', None)
    authorize_username = request.session.pop('authorize_username', None)
    if authorize_username and authorize_username == username:
      sp_oauth = spotofo.oauth_client()
      token_info = sp_oauth.get_access_token(code)
      if token_info:
        sp_user = spotofo.save_token_info(username, token_info)
        user,_ = User.objects.get_or_create(username=username)
        sp_user.user = user
        sp_user.save()
        user.backend = 'django.contrib.auth.backends.ModelBackend'
        auth_login(request, user)
        # TODO Remove this when playlist management has been implemented
        for pl in Playlist.objects.all():
          sp_user.playlists.add(pl)
        # TODO Remove this when device management has been implemented
        for d in spotofo.get_user_devices(username):
          spotofo.add_user_device(username, d)
    return HttpResponseRedirect('/')

