
from django.db import models
from django.contrib.auth.models import User as DjangoUser


class Playlist(models.Model):
  spid = models.CharField(max_length=2048)
  spuser = models.CharField(max_length=2048)

  def uri(self):
    return 'spotify:user:%s:playlist:%s'%(self.spuser, self.spid)

  def open_url(self):
    return 'https://open.spotify.com/user/%s/playlist/%s'%(self.spuser, self.spid)

  @classmethod
  def split_uri(cls, target):
    m = re.match('spotify:user:([^:]*):playlist:(.*)', target)
    if not m:
      return (None, None)
    username = m.group(1)
    playlist = m.group(2)
    return (username, playlist)

  def __str__(self):
    return self.uri()


class Device(models.Model):
  spid = models.CharField(max_length=2048)
  name = models.CharField(max_length=2048)

  def __str__(self):
    return self.spid


class SpotifyUser(models.Model):
  username = models.CharField(max_length=2048) # TODO index
  user = models.ForeignKey(DjangoUser, related_name='spotify', null=True)
  devices = models.ManyToManyField(Device, related_name='users', blank=True)
  playlists = models.ManyToManyField(Playlist, related_name='users', blank=True)
  token_info = models.CharField(max_length=2048, null=True, blank=True)

  class Meta:
    verbose_name = 'User'

  def __str__(self):
    return self.username


class MqttTopic(models.Model):
  topic = models.CharField(max_length=2048)
  username = models.CharField(max_length=2048)
  host = models.CharField(max_length=2048)
  port = models.IntegerField()
  password = models.CharField(max_length=2048)


