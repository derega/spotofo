
from django.conf.urls import url
from django.contrib import admin
from spotofoweb.views import CurrentlyPlayingView

urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^$', CurrentlyPlayingView.as_view()),
]

