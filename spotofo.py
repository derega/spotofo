
from __future__ import print_function
import re
import json
import codecs
import logging
from collections import namedtuple
import spotipy
from django.core.cache import cache
from spotofoweb.models import SpotifyUser, Device, Playlist, Play, MqttTopic
from spotofoweb import config


DEFAULT_SCOPE = 'user-read-playback-state'

LOG = logging.getLogger(__name__)


def _pd(d):
  print(json.dumps(d, indent=2))


### Spotify data handling functions

TrackInfo = namedtuple('TrackInfo', ('username', 'track', 'album', 'artist', 'uri', 'device', 'progress', 'is_playing', 'active_device', 'raw'))

def get_all_tracks_from_playlist(playlist):
  sp = spotify_client(playlist.spuser)
  if not sp: return set()
  tracks = []
  def get_tracks(trs):
    for t in trs:
      tracks.append(t['track'])
  results = sp.user_playlist_tracks(playlist.spuser, playlist.spid)
  get_tracks(results['items'])
  while results['next']:
    results = sp.next(results)
    get_tracks(results['items'])
  return tracks


def deduplicate_tracks(tracks):
  to_be_added = set()
  playlist = get_playlist()
  if playlist:
    sp = spotify_client(playlist.spuser)
    if sp:
      tracks_in_playlist = get_all_tracks_from_playlist(playlist)
      existing = map(lambda x: x['uri'], tracks_in_playlist)
      to_be_added = set(tracks) - set(existing)
  return to_be_added


def add_tracks_to_playlist(tracks):
  if len(tracks) > 0:
    playlist = get_playlist()
    if playlist:
      sp = spotify_client(playlist.spuser)
      if sp:
        sp.user_playlist_add_tracks(playlist.spuser, playlist.spid, tracks, position=0)


def get_user_devices(username):
  devices = []
  sp = spotify_client(username)
  if sp:
    r = sp._get('me/player/devices')
    if r and 'devices' in r:
      devices = r['devices']
  return devices


def get_currently_playing_trackinfo(usernames):
  for username in usernames:
    cache_key = u'currently_playing-%s'%(username)
    data = cache.get(cache_key)
    if data:
      try:
        yield TrackInfo(**data)
      except TypeError:
        pass # will reset on cache invalidation timeout
    else:
      sp = spotify_client(username)
      if sp:
        try:
          r = sp._get('me/player')
          track = r['item']
          duration_ms = float(r['item']['duration_ms'])
          progress_ms = float(r['progress_ms'])
          progress = progress_ms / duration_ms
          data = {
            'username': username,
            'track': track['name'],
            'album': track['album']['name'],
            'artist': track['artists'][0]['name'],
            'uri': track['uri'],
            'device': r['device']['id'],
            'progress': progress,
            'is_playing': r['is_playing'],
            'active_device': is_authorized_device(username, r['device']['id']),
            'raw': r
            }
          cache.set(cache_key, data, 55)
          yield TrackInfo(**data)
        except Exception:
          LOG.exception('Cannot query currently playing track')


### MQTT functions

def mqtt_single(payload, topic=None):
  try:
    from paho.mqtt.publish import single
  except ImportError:
    print('Install paho-mqtt')
    return
  arg_topic, kwargs = get_mqtt_config()
  kwargs['payload'] = payload
  if topic: arg_topic = topic
  #print(repr(arg_topic), repr(kwargs['payload']))
  single(arg_topic, **kwargs)


### Config and data handling functions

def get_mqtt_config():
  topic = None
  hostname = None
  port = 1883
  auth = None
  if MqttTopic.objects.exists():
    m = MqttTopic.objects.filter()[0]
    auth = {'username': m.username, 'password': m.password}
    hostname = m.host
    port = m.port
    topic = m.topic
  kwargs = {
    'qos': 0,
    'retain': False,
    'hostname': hostname,
    'port': port,
    'client_id': None,
    'keepalive': 60,
    'will': None,
    'auth': auth,
    'tls': None,
    'transport': 'tcp',
    }
  return topic, kwargs


def set_mqtt_config(host, port=1883, topic='spotofo', username=None, password=None):
  m,_ = MqttTopic.objects.get_or_create(topic=topic, host=host, port=port, username=username, password=password)
  m.save()


def add_user_device(username, device):
  d,_ = Device.objects.get_or_create(spid=device['id'])
  d.name = device['name']
  d.save()
  user = SpotifyUser.objects.get(username=username)
  user.devices.add(d)


def get_users():
  return [u.username for u in SpotifyUser.objects.all()]


def is_authorized_device(username, device):
  if Device.objects.filter(spid=device).exists():
    return True
  return False


def get_devices(username):
  u = SpotifyUser.objects.get(username=username)
  return [d.spid for d in u.devices.all()]


def save_playlist(username, playlist):
  pl,_ = Playlist.objects.get_or_create(spid=playlist, spuser=username)
  pl.save()
  u = SpotifyUser.objects.get(username=username)
  u.playlists.add(pl)


def split_playlist(target):
  return Playlist.split_uri(target)


def get_playlist():
  try:
    return Playlist.objects.all()[0]
  except IndexError:
    return None


def save_token_info(username, token_info):
  u,_ = SpotifyUser.objects.get_or_create(username=username)
  u.token_info = json.dumps(token_info)
  u.save()
  return u


def get_token_info(username):
  """Get access token from config
  Refreshes the token if it has been expired.
  Saves the token to config when refreshing.
  """
  client = oauth_client()
  token_info = None
  try:
    user = SpotifyUser.objects.get(username=username)
    if user.token_info:
      token_info = json.loads(user.token_info)
    if token_info and client.is_token_expired(token_info):
      token_info = client.refresh_access_token(token_info['refresh_token'])
      if token_info:
        user.token_info = json.dumps(token_info)
        user.save()
  except SpotifyUser.DoesNotExist:
    pass
  return token_info


def spotify_client(username):
  sp = None
  token_info = get_token_info(username)
  if token_info:
    sp = spotipy.Spotify(auth=token_info['access_token'], requests_timeout=10)
  return sp


### Analyze

def influx_write(meas, tags, name, value):
  url = config.INFLUX_WRITE_URL
  if not url: return
  import requests
  for n,v in tags.iteritems():
    meas = meas + u',%s=%s'%(n,v)
  data = u'%s %s=%s' % (meas, name, str(value))
  r = requests.post(url, data=data)

def play_write(trackinfo):
  if trackinfo.is_playing:
    raw = trackinfo.raw
    defaults = {
    # From trackinfo:
      'username': trackinfo.username,
      'track': trackinfo.track,
      'artist': trackinfo.artist,
      'album': trackinfo.album,
      'track_uri': trackinfo.uri,
    # Parsed from raw:
      'device_type': raw['device']['type'],
      'album_uri': raw['item']['album']['uri'],
      'artist_uri': raw['item']['album']['artists'][0]['uri'],
      'volume_percent': raw['device']['volume_percent'],
      'duration_ms': raw['item']['duration_ms'],
      'popularity': raw['item']['popularity'],
      'explicit': raw['item']['explicit'],
      'json_string': json.dumps(raw),
      }
    data = {
      'user': SpotifyUser.objects.get(username=trackinfo.username),
      'device': Device.objects.get(spid=trackinfo.device),
      'timestamp': raw['timestamp'],
      'defaults': defaults,
      }
    play, created = Play.objects.get_or_create(**data)
    if created:
      play.save()


def analyze_play(trackinfo):
  play_write(trackinfo)
  influx_write('spotofo.play', {'user': trackinfo.username}, 'count', '1i')


### oAuth functions

def oauth_client(scope=None):
  import spotipy.oauth2
  kwargs = {
    'scope': scope or DEFAULT_SCOPE,
    'client_id': config.CLIENT_ID,
    'client_secret': config.CLIENT_SECRET,
    'redirect_uri': config.REDIRECT_URI,
    }
  sp_oauth = spotipy.oauth2.SpotifyOAuth(**kwargs)
  return sp_oauth


def authorize_with_scope(username, scope=None, response=None):
  """Authorize Spotify API usage.

  First call without response argument.
  Then call again with the URL you got from Spotify as the response argument.
  """
  sp_oauth = oauth_client(scope=scope)
  if response:
    code = sp_oauth.parse_response_code(response)
    token_info = sp_oauth.get_access_token(code)
    return ('token', token_info)
  else:
    auth_url = sp_oauth.get_authorize_url()
    return ('auth_url', auth_url)


