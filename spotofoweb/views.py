
from django.core.cache import cache
from django.views.generic import TemplateView
import spotofo

class CurrentlyPlayingView(TemplateView):
  template_name = 'spotofoweb/currently_playing.html'

  def get_context_data(self, **kwargs):
    context = super(TemplateView, self).get_context_data(**kwargs)
    cp = cache.get('currently_playing')
    if not cp:
      users = spotofo.get_users()
      print 'QUERY'
      cp = list(spotofo.get_currently_playing_trackinfo(users))
      cache.set('currently_playing', cp, 60)
    context['currently_playing'] = cp
    return context

