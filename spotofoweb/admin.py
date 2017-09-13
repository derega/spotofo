
from django.contrib import admin
from . import models


class SpotifyUserInline(object):
  fields = ('username', 'device_count', 'playlist_count')
  readonly_fields = ['username', 'device_count', 'playlist_count']
  verbose_name = 'User'
  verbose_name_plural = 'Users'
  extra = 0
  can_delete = False

  def username(self, instance):
    return instance.spotifyuser.username

  def device_count(self, instance):
    return instance.spotifyuser.devices.all().count()

  def playlist_count(self, instance):
    return instance.spotifyuser.playlists.all().count()

  def has_add_permission(self, request):
    return False


class SpotifyUserPlaylistInline(SpotifyUserInline, admin.TabularInline):
  model = models.SpotifyUser.playlists.through


class PlaylistAdmin(admin.ModelAdmin):
  list_display = ('spid', 'spuser', 'uri')
  readonly_fields = ('uri',)
  inlines = [SpotifyUserPlaylistInline]

  def uri(self, instance):
    username = instance.spuser
    spid = instance.spid
    return 'spotify:user:%s:playlist:%s'%(username, spid)


class PlayAdmin(admin.ModelAdmin):
  list_display = ('timestamp', 'playtime', 'track', 'artist', 'album', 'username', 'device_type', 'volume_percent', 'duration_ms', 'popularity', 'explicit')


class SpotifyUserDeviceInline(SpotifyUserInline, admin.TabularInline):
  model = models.SpotifyUser.devices.through


class DeviceAdmin(admin.ModelAdmin):
  list_display = ('spid', 'name')
  inlines = [SpotifyUserDeviceInline]


class DeviceInline(admin.TabularInline):
  model = models.SpotifyUser.devices.through
  fields = ('spid', 'name')
  readonly_fields = ('spid', 'name')
  verbose_name = 'Device'
  verbose_name_plural = 'Devices'
  extra = 0
  can_delete = False

  def spid(self, instance):
    return instance.device.spid

  def name(self, instance):
    return instance.device.name

  def has_add_permission(self, request):
    return False


class PlaylistInline(admin.TabularInline):
  model = models.SpotifyUser.playlists.through
  fields = ('spid', 'name', 'uri')
  readonly_fields = ('spid', 'name', 'uri')
  verbose_name = 'Playlist'
  verbose_name_plural = 'Playlists'
  extra = 0
  can_delete = False

  def spid(self, instance):
    return instance.playlist.spid

  def name(self, instance):
    return instance.playlist.spuser

  def uri(self, instance):
    spuser = instance.playlist.spuser
    spid = instance.playlist.spid
    return 'spotify:user:%s:playlist:%s'%(spuser, spid)

  def has_add_permission(self, request):
    return False


class SpotifyUserAdmin(admin.ModelAdmin):
  list_display = ('username', 'device_count', 'playlist_count')
  raw_id_fields = ('user',)
  inlines = [DeviceInline, PlaylistInline]
  exclude = ('devices', 'playlists')

  def device_count(self, instance):
    return instance.devices.all().count()

  def playlist_count(self, instance):
    return instance.playlists.all().count()


class MqttTopicAdmin(admin.ModelAdmin):
  list_display = ('topic', 'host', 'port', 'username')


class UserPlaylistAdmin(admin.ModelAdmin):
  raw_id_fields = ('spotifyuser', 'playlist')
  list_display = ('spotifyuser', 'playlist')

admin.site.register(models.Playlist, PlaylistAdmin)
admin.site.register(models.Play, PlayAdmin)
admin.site.register(models.Device, DeviceAdmin)
admin.site.register(models.SpotifyUser, SpotifyUserAdmin)
admin.site.register(models.MqttTopic, MqttTopicAdmin)
admin.site.register(models.SpotifyUser.playlists.through, UserPlaylistAdmin)



