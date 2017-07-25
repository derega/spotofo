
import os
import sys
import re
import json
import codecs
from collections import namedtuple

import click
import spotipy


DEFAULT_SCOPE = 'user-read-playback-state'


def _pd(d):
  print json.dumps(d, indent=2)


### Spotify data handling functions

TrackInfo = namedtuple('TrackInfo', ('username', 'track', 'album', 'artist', 'uri', 'device'))

def get_all_tracks_from_playlist(config, playlist):
  username, playlist_id = _split_playlist(playlist)
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
    username, playlist_id = _split_playlist(playlist)
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
      username, playlist_id = _split_playlist(playlist)
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


def _split_playlist(target):
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
    if client.is_token_expired(token_info):
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


def _oauth_authorize(config, username, scope=None, response=None):
  state, data = authorize_with_scope(config, username, scope=scope)
  print('Please navigate here: %s' % data)
  response = raw_input('Enter the URL you were redirected to: ')
  state, data = authorize_with_scope(config, username, scope=scope, response=response)
  return state, data


### The CLI :)

@click.group()
@click.option('-c', 'cfn', help='Config file', default=os.path.expanduser('~/.spotofo.conf'))
@click.pass_context
def cli(ctx, cfn):
  ctx.obj = get_config(cfn)


@cli.command()
@click.pass_context
def currently_playing(ctx):
  for trackinfo in get_currently_playing_trackinfo(ctx.obj, get_users(ctx.obj)):
    print trackinfo


@cli.command()
@click.pass_context
@click.argument('track')
def add_track(ctx, track):
  to_be_added_tracks = deduplicate_tracks(ctx.obj, [track])
  add_tracks_to_playlist(ctx.obj, to_be_added_tracks)


@cli.command()
@click.pass_context
def update_shared_playlist(ctx):
  tracks = []
  for ti in get_currently_playing_trackinfo(ctx.obj, get_users(ctx.obj)):
    if is_authorized_device(ctx.obj, ti.username, ti.device):
      tracks.append(ti)
  track_uris = map(lambda x: x.uri, tracks)
  to_be_added_tracks = deduplicate_tracks(ctx.obj, track_uris)
  add_tracks_to_playlist(ctx.obj, to_be_added_tracks)
  for ti in tracks:
    print ti, ti.uri in to_be_added_tracks


@cli.command()
@click.argument('username')
@click.pass_context
def authorize(ctx, username):
  state, data = _oauth_authorize(ctx.obj, username, scope=DEFAULT_SCOPE)
  if state == 'token' and data:
    save_token_info(ctx.obj, username, data)
    devices = get_user_devices(ctx.obj, username)
    device_ids = []
    for device in devices:
      print device['type'], repr(device['name']), 'ID:', device['id']
      device_ids.append(device['id'])
    device = raw_input('Enter the device ID you want to authorize: ')
    if device in device_ids:
      add_user_device(ctx.obj, username, device)
      save_config(ctx.obj)
      print 'Authorized to query data from user', username, 'device', device
    else:
      print "Can't authorize device", device
  else:
    print "Can't get token for", username


@cli.command()
@click.argument('username')
@click.pass_context
def devices(ctx, username):
  devices = get_user_devices(ctx.obj, username)
  for device in devices:
    print device['type'], repr(device['name']), 'ID:', device['id']


@cli.command()
@click.pass_context
def authorized(ctx):
  print 'Authorized to query data from user / device:'
  for username in get_users(ctx.obj):
    for device in get_devices(ctx.obj, username):
      print username, '/', device


@cli.command()
@click.argument('target')
@click.pass_context
def playlist(ctx, target):
  username, playlist = _split_playlist(target)
  if not username:
    print 'Unable to handle playlist'
    return
  scope = 'playlist-modify-private'
  state, data = _oauth_authorize(ctx.obj, username, scope=scope)
  if state == 'token' and data:
    save_token_info(ctx.obj, username, data)
    save_playlist(ctx.obj, username, playlist)
    save_config(ctx.obj)
    print 'Authorized to change playlist', target
  else:
    print "Can't get token for", username


if __name__ == '__main__':
  cli()

