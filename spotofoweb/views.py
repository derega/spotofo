
from django.core.cache import cache
from django import forms
from django.http import HttpResponseRedirect
from django.views.generic import View, FormView, TemplateView
import spotofo


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
    url = sp_oauth.get_authorize_url(state=username)
    self.success_url = url
    return super(FormView, self).form_valid(form)


class AuthorizeResponseView(View):
  def get(self, request, *args, **kwargs):
    code = request.GET.get('code', None)
    username = request.GET.get('state', None)
    sp_oauth = spotofo.oauth_client()
    token_info = sp_oauth.get_access_token(code)
    spotofo.save_token_info(username, token_info)
    return HttpResponseRedirect('/')

