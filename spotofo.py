
import sys
import json
import codecs

import click
import spotipy


def get_currently_playing(auth_token=None):
  sp = spotipy.Spotify(auth_token)
  r = sp._get('me/player')
  return r


def get_currently_playing_trackinfo(auth_token=None):
  r = get_currently_playing(auth_token)
  track = r['item']
  album = track['album']
  artist = track['artists'][0]

  return (track['name'], album['name'], artist['name'])


@click.command()
@click.option('-c', 'config', help='Config file')
def main(config):
  data = codecs.open(config, 'r')
  data = json.loads(data.read())

  for user,at in data['authtokens'].iteritems():
    print repr(get_currently_playing_trackinfo(at))


if __name__ == '__main__':
  main()

