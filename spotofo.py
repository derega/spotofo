
import os
import sys
import re
import json
import codecs

import click
import spotipy


DEFAULT_SCOPE = 'user-read-playback-state'


def _pd(d):
  print json.dumps(d, indent=2)


### Spotify data handling functions

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


def add_tracks_to_playlist(config, tracks):
  playlist = get_playlist(config)
  username, playlist_id = _split_playlist(playlist)
  sp = spotify_client(config, username)
  if sp:
    tracks_in_playlist = get_all_tracks_from_playlist(config, playlist)
    existing = map(lambda x: x['uri'], tracks_in_playlist)
    to_be_added = set(tracks) - set(existing)
    if len(to_be_added) > 0:
      print repr(playlist), repr(to_be_added)
      sp.user_playlist_add_tracks(username, playlist, to_be_added, position=0)


def get_currently_playing_trackinfo(config, usernames):
  for username in usernames:
    token_info = get_token_info(config, username)
    if token_info:
      sp = spotipy.Spotify(token_info['access_token'])
      r = sp._get('me/player')
      track = r['item']
      album = track['album']
      artist = track['artists'][0]
      yield (r, username, track['name'], album['name'], artist['name'])


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


def add_user(config, username):
  if not 'users' in config:
    config['users'] = []
  if not username in config['users']:
    config['users'].append(username)


def get_users(config):
  users = []
  if 'users' in config:
    users = config['users']
  return users


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
  client = oauth_client(config, username)
  if username in config['token_info']:
    client.token_info = config['token_info'][username]
    stored_token = client.token_info['access_token']
    queried_token = client.get_access_token()
    if stored_token != queried_token:
      save_token_info(config, username, client.token_info)
      save_config(config)
  return client.token_info


def spotify_client(config, username):
  token_info = get_token_info(config, username)
  sp = None
  if token_info:
    sp = spotipy.Spotify(token_info['access_token'])
  return sp


### oAuth functions

def oauth_client(config, username):
  import spotipy.oauth2
  kwargs = {
    'client_id': config['client_id'],
    'client_secret': config['client_secret'],
    }
  sp_oauth = spotipy.oauth2.SpotifyClientCredentials(**kwargs)
  return sp_oauth


def authorize_with_scope(config, username, scope=None, response=None):
  """Authorize Spotify API usage.

  First call without response argument.
  Then call again with the URL you got from Spotify as the response argument.
  """
  import spotipy.oauth2
  kwargs = {
    'scope': scope or DEFAULT_SCOPE,
    'client_id': config['client_id'],
    'client_secret': config['client_secret'],
    'redirect_uri': config['redirect_uri'],
    }
  sp_oauth = spotipy.oauth2.SpotifyOAuth(**kwargs)
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
    print repr(trackinfo[1:])


def add_track_to_playlist(config, track, playlist):
  print track, playlist

@cli.command()
@click.pass_context
def update_shared_playlist(ctx):
  tracks = []
  for trackinfo in get_currently_playing_trackinfo(ctx.obj, get_users(ctx.obj)):
    uri = trackinfo[0]['item']['uri']
    tracks.append(uri)
  add_tracks_to_playlist(ctx.obj, tracks)


@cli.command()
@click.argument('username')
@click.pass_context
def authorize(ctx, username):
  state, data = _oauth_authorize(ctx.obj, username, scope=DEFAULT_SCOPE)
  if state == 'token' and data:
    save_token_info(ctx.obj, username, data)
    add_user(ctx.obj, username)
    save_config(ctx.obj)
    print 'Authorized to query data from user', username
  else:
    print "Can't get token for", username


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

