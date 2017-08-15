
import re
import json
import codecs
from collections import namedtuple

import spotipy


DEFAULT_SCOPE = 'user-read-playback-state'


def _pd(d):
  print json.dumps(d, indent=2)


### Spotify data handling functions

TrackInfo = namedtuple('TrackInfo', ('username', 'track', 'album', 'artist', 'uri', 'device'))

def get_all_tracks_from_playlist(config, playlist):
  username, playlist_id = split_playlist(playlist)
  sp = spotify_client(config, username)
  if not sp: return set()
  tracks = []
  def get_tracks(trs):
    for t in trs:
      tracks.append(t['track'])
  results = sp.user_playlist_tracks(username, playlist)
  get_tracks(results['items'])
  while results['next']:
    results = sp.next(results)
    get_tracks(results['items'])
  return tracks


def deduplicate_tracks(config, tracks):
  to_be_added = set()
  playlist = get_playlist(config)
  if playlist:
    username, playlist_id = split_playlist(playlist)
    sp = spotify_client(config, username)
    if sp:
      tracks_in_playlist = get_all_tracks_from_playlist(config, playlist)
      existing = map(lambda x: x['uri'], tracks_in_playlist)
      to_be_added = set(tracks) - set(existing)
  return to_be_added


def add_tracks_to_playlist(config, tracks):
  if len(tracks) > 0:
    playlist = get_playlist(config)
    if playlist:
      username, playlist_id = split_playlist(playlist)
      sp = spotify_client(config, username)
      if sp:
        sp.user_playlist_add_tracks(username, playlist, tracks, position=0)


def get_user_devices(config, username):
  devices = []
  sp = spotify_client(config, username)
  if sp:
    r = sp._get('me/player/devices')
    devices = r['devices']
  return devices


def get_currently_playing_trackinfo(config, usernames):
  for username in usernames:
    sp = spotify_client(config, username)
    if sp:
      try:
        r = sp._get('me/player')
        track = r['item']
        data = {
          'username': username,
          'track': track['name'],
          'album': track['album']['name'],
          'artist': track['artists'][0]['name'],
          'uri': track['uri'],
          'device': r['device']['id'],
          }
        yield TrackInfo(**data)
      except Exception, e:
        print repr(e)

### MQTT functions

def mqtt_single(config, payload, topic=None):
  try:
    from paho.mqtt.publish import single
  except ImportError:
    print 'Install paho-mqtt'
    return
  arg_topic, kwargs = get_mqtt_config(config)
  kwargs['payload'] = payload
  if topic: arg_topic = topic
  #print repr(arg_topic), repr(kwargs['payload'])
  single(arg_topic, **kwargs)


### Config and data handling functions

def get_config(filename):
  try:
    with codecs.open(filename, 'r') as f:
      config = json.loads(f.read())
  except IOError:
    # Initialize empty config
    config = {
      'client_id': '',
      'client_secret': '',
      'redirect_uri': '',
      }
  config['config_filename'] = filename
  save_config(config)
  return config


def save_config(config):
  fn = config['config_filename']
  with codecs.open(fn, 'w') as f:
    f.write(json.dumps(config))


def get_mqtt_config(config):
  auth = None
  if config['mqtt']['username'] and config['mqtt']['password']:
    auth = {'username': config['mqtt']['username'], 'password': config['mqtt']['password']}
  kwargs = {
    'qos': 0,
    'retain': False,
    'hostname': config['mqtt']['host'],
    'port': int(config['mqtt']['port']),
    'client_id': None,
    'keepalive': 60,
    'will': None,
    'auth': auth,
    'tls': None,
    'transport': 'tcp',
    }
  return config['mqtt']['topic'], kwargs


def set_mqtt_config(config, host, port=1883, topic='spotofo', username=None, password=None):
  config['mqtt'] = {
    'host': host,
    'port': int(port),
    'topic': topic,
    'username': username,
    'password': password,
  }
  save_config(config)


def add_user_device(config, username, device):
  if not 'users' in config:
    config['users'] = {}
  if not username in config['users']:
    config['users'][username] = {'username': username, 'devices': [device]}
  if not device in config['users'][username]['devices']:
    config['users'][username]['devices'].append(device)


def get_users(config):
  users = []
  if 'users' in config:
    users = config['users']
  return users


def is_authorized_device(config, username, device):
  for user in config['users']:
    if device in config['users'][user]['devices']:
      return True
  return False


def get_devices(config, username):
  users = get_users(config)
  devices = []
  if username in users:
    devices = users[username]['devices']
  return devices


def save_playlist(config, username, playlist):
  config['playlist'] = 'spotify:user:%s:playlist:%s'%(username, playlist)


def split_playlist(target):
  m = re.match('spotify:user:([^:]*):playlist:(.*)', target)
  if not m:
    return (None, None)
  username = m.group(1)
  playlist = m.group(2)
  return (username, playlist)


def get_playlist(config):
  playlist = None
  if 'playlist' in config:
    playlist = config['playlist']
  return playlist


def save_token_info(config, username, token_info):
  if not 'token_info' in config:
    config['token_info'] = {}
  config['token_info'][username] = token_info


def get_token_info(config, username):
  """Get access token from config
  Refreshes the token if it has been expired.
  Saves the token to config when refreshing.
  """
  client = oauth_client(config)
  token_info = None
  if username in config['token_info']:
    token_info = config['token_info'][username]
    if token_info and client.is_token_expired(token_info):
      token_info = client.refresh_access_token(token_info['refresh_token'])
      save_token_info(config, username, token_info)
      save_config(config)
  return token_info


def spotify_client(config, username):
  sp = None
  token_info = get_token_info(config, username)
  if token_info:
    sp = spotipy.Spotify(auth=token_info['access_token'], requests_timeout=10)
  return sp


### Analyze

def influx_write(config, meas, tags, name, value):
  url = config.get('influx_write_url', None)
  if not url: return
  import requests
  for n,v in tags.iteritems():
    meas = meas + u',%s=%s'%(n,v)
  data = u'%s %s=%s' % (meas, name, str(value))
  r = requests.post(url, data=data)


def analyze_play(config, trackinfo):
  influx_write(config, 'spotofo.play', {'user': trackinfo.username}, 'count', '1i')


### oAuth functions

def oauth_client(config, scope=None):
  import spotipy.oauth2
  kwargs = {
    'scope': scope,
    'client_id': config['client_id'],
    'client_secret': config['client_secret'],
    'redirect_uri': config['redirect_uri'],
    }
  sp_oauth = spotipy.oauth2.SpotifyOAuth(**kwargs)
  return sp_oauth


def authorize_with_scope(config, username, scope=None, response=None):
  """Authorize Spotify API usage.

  First call without response argument.
  Then call again with the URL you got from Spotify as the response argument.
  """
  scope = scope or DEFAULT_SCOPE
  sp_oauth = oauth_client(config, scope=scope)
  if response:
    code = sp_oauth.parse_response_code(response)
    token_info = sp_oauth.get_access_token(code)
    return ('token', token_info)
  else:
    auth_url = sp_oauth.get_authorize_url()
    return ('auth_url', auth_url)


