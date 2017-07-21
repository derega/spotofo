
import os
import sys
import json
import codecs

import click
import spotipy


DEFAULT_SCOPE = 'user-read-playback-state'


def get_currently_playing(auth_token=None):
  sp = spotipy.Spotify(auth_token)
  r = sp._get('me/player')
  return r


def save_config(config):
  fn = config['config_filename']
  with codecs.open(fn, 'w') as f:
    f.write(json.dumps(config))


def add_user(config, username):
  if not 'users' in config:
    config['users'] = []
  if not username in config['users']:
    config['users'].append(username)


def save_token_info(config, username, token_info):
  if not 'token_info' in config:
    config['token_info'] = {}
  config['token_info'][username] = token_info


def get_token_info(config, username):
  """Get access token from config
  Refreshes the token if it has been expired.
  Saves the token to config when refreshing.
  """
  sp_oauth = _oauth(config, username)
  if username in config['token_info']:
    sp_oauth.token_info = config['token_info'][username]
    stored_token = sp_oauth.token_info['access_token']
    queried_token = sp_oauth.get_access_token()
    if stored_token != queried_token:
      save_token_info(config, username, sp_oauth.token_info)
      save_config(config)
  return sp_oauth.token_info


def _oauth(config, username):
  import spotipy.oauth2
  kwargs = {
    'client_id': config['client_id'],
    'client_secret': config['client_secret'],
    }
  sp_oauth = spotipy.oauth2.SpotifyClientCredentials(**kwargs)
  return sp_oauth


@click.group()
@click.option('-c', 'config', help='Config file', default=os.path.expanduser('~/.spotofo.conf'))
@click.pass_context
def cli(ctx, config):
  try:
    with codecs.open(config, 'r') as f:
      ctx.obj = json.loads(f.read())
  except IOError:
    ctx.obj = {
      'client_id': '',
      'client_secret': '',
      'redirect_uri': '',
      }
    ctx.obj['config_filename'] = config
    save_config(ctx.obj)
  ctx.obj['config_filename'] = config


def get_currently_playing_trackinfo(config, usernames):
  for username in usernames:
    token_info = get_token_info(config, username)
    if token_info:
      r = get_currently_playing(token_info['access_token'])
      track = r['item']
      album = track['album']
      artist = track['artists'][0]
      yield (r, username, track['name'], album['name'], artist['name'])


@cli.command()
@click.pass_context
def currently_playing(ctx):
  if 'users' in ctx.obj:
    for trackinfo in get_currently_playing_trackinfo(ctx.obj, ctx.obj['users']):
      print repr(trackinfo[1:])


@cli.command()
@click.argument('username')
@click.pass_context
def authorize(ctx, username):
  import spotipy.oauth2
  kwargs = {
    'scope': DEFAULT_SCOPE,
    'client_id': ctx.obj['client_id'],
    'client_secret': ctx.obj['client_secret'],
    'redirect_uri': ctx.obj['redirect_uri'],
    }
  sp_oauth = spotipy.oauth2.SpotifyOAuth(**kwargs)
  auth_url = sp_oauth.get_authorize_url()

  print("Please navigate here: %s" % auth_url)
  response = raw_input("Enter the URL you were redirected to: ")

  code = sp_oauth.parse_response_code(response)
  token_info = sp_oauth.get_access_token(code)
  save_token_info(ctx.obj, username, token_info)
  add_user(ctx.obj, username)
  save_config(ctx.obj)

  if token_info:
    print 'Token saved.'
  else:
    print "Can't get token for", username


if __name__ == '__main__':
  cli()

