
from django.conf.urls import url
from django.contrib import admin
from spotofoweb.views import CurrentlyPlayingView
from spotofoweb.views import AuthorizeUserView, AuthorizeResponseView

urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^$', CurrentlyPlayingView.as_view()),
    url(r'^authorize$', AuthorizeUserView.as_view()),
    url(r'^authorize/response$', AuthorizeResponseView.as_view()),
]

