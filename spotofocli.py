
import django
django.setup()

import os
import json
import click
import spotofo


@click.group()
@click.option('-c', 'cfn', help='Config file', default=os.path.expanduser('~/.spotofo.conf'))
@click.pass_context
def cli(ctx, cfn):
  pass


@cli.command()
@click.pass_context
def currently_playing(ctx):
  """Currently playing tracks for all users"""
  for trackinfo in spotofo.get_currently_playing_trackinfo(spotofo.get_users()):
    print trackinfo


@cli.command()
@click.pass_context
@click.option('--topic', help='Topic to subscribe', default=None)
def update_playlist(ctx, topic):
  """Add currently playing tracks to the playlist

  Only add tracks which are not yet in the playlist.
  Only add tracks playing in authorized devices.
  Send information about added tracks to MQTT topic if configured.
  """
  tracks, track_uris, added_tracks = _update_shared_playlist()
  data = [x for x in tracks if x.uri in added_tracks]
  for ti in tracks:
    print ti
  if len(data):
    spotofo.mqtt_single(json.dumps(data), topic)


@cli.command()
@click.pass_context
@click.argument('track')
def add_track(ctx, track):
  """Add track to playlist"""
  to_be_added_tracks = spotofo.deduplicate_tracks([track])
  spotofo.add_tracks_to_playlist(to_be_added_tracks)


@cli.command()
@click.pass_context
@click.argument('host')
@click.option('--port', default=1883)
@click.option('--topic', default='spotofo')
@click.option('--username', default=None)
@click.option('--password', default=None)
def mqtt_config(ctx, host, port, topic, username, password):
  """Set MQTT connection parameters"""
  spotofo.set_mqtt_config(host, port, topic, username, password)
  print repr(spotofo.get_mqtt_config())


@cli.command()
@click.pass_context
@click.argument('msg')
@click.option('--topic', default=None)
def mqtt_send(ctx, msg, topic):
  """Send message to MQTT topic"""
  try:
    spotofo.mqtt_single(msg, topic)
  except ValueError, e:
    print e
    return


@cli.command()
@click.pass_context
@click.option('--host', default=None)
@click.option('--port', default=None)
@click.option('--topic', help='Topic to subscribe', default=None)
@click.option('--username', default=None)
@click.option('--password', default=None)
def mqtt_client(ctx, host, port, topic, username, password):
  """Monitor MQTT topic for messages"""
  try:
    import paho.mqtt.client as mqtt
  except ImportError:
    print 'Install paho-mqtt'
    return
  topic_arg, conf = spotofo.get_mqtt_config()
  topic_arg = topic or topic_arg
  try:
    username = username or conf['auth']['username']
    password = password or conf['auth']['password']
  except TypeError:
    username = None
    password = None
  host = host or conf['hostname']
  port = port or conf['port']
  def on_connect(client, userdata, flags, rc):
    if rc == 0:
      client.subscribe(topic_arg)
      print 'Subscribed:', repr(topic_arg)
    else:
      print mqtt.error_string(rc)
  def on_message(client, userdata, msg):
    print repr(msg.topic), repr(msg.payload)
  client = mqtt.Client()
  client.on_connect = on_connect
  client.on_message = on_message
  if username and password:
    client.username_pw_set(username, password)
  try:
    client.connect(host, int(port), 60)
  except ValueError, e:
    print e
    return
  client.loop_forever()


@cli.command()
@click.argument('username')
@click.pass_context
def devices(ctx, username):
  """List available devices for user"""
  devices = spotofo.get_user_devices(username)
  for device in devices:
    print device['type'], repr(device['name']), 'ID:', device['id']


@cli.command()
@click.pass_context
def authorized(ctx):
  """List authorized users and devices"""
  print 'Authorized to query data from user / device:'
  for username in spotofo.get_users():
    for device in spotofo.get_devices(username):
      print username, '/', device


@cli.command()
@click.pass_context
def config(ctx):
  """Show config"""
  print 'Nothing to show'


@cli.command()
@click.argument('username')
@click.pass_context
def authorize_user(ctx, username):
  """Add new user"""
  state, data = _oauth_authorize(username, scope=spotofo.DEFAULT_SCOPE)
  if state == 'token' and data:
    spotofo.save_token_info(username, data)
    print 'Authorized to query data from user', username
  else:
    print "Can't get token for", username


@cli.command()
@click.argument('username')
@click.pass_context
def authorize_device(ctx, username):
  """Add new device"""
  devices = spotofo.get_user_devices(username)
  device_ids = []
  if devices:
    for device in devices:
      print device['type'], repr(device['name']), 'ID:', device['id']
      device_ids.append(device['id'])
    device_id = raw_input('Enter the device ID you want to authorize: ')
    for device in devices:
      if device_id == device['id']:
        spotofo.add_user_device(username, device)
        print 'Authorized to query data from user', username, 'device', device['id']
        return
    print "Can't authorize device", device


@cli.command()
@click.argument('target')
@click.pass_context
def authorize_playlist(ctx, target):
  """Change target playlist"""
  username, playlist = spotofo.split_playlist(target)
  if not username:
    print 'Unable to handle playlist'
    return
  scope = 'playlist-modify-private'
  state, data = _oauth_authorize(username, scope=scope)
  if state == 'token' and data:
    spotofo.save_token_info(username, data)
    spotofo.save_playlist(username, playlist)
    print 'Authorized to change playlist', target
  else:
    print "Can't get token for", username


def _update_shared_playlist():
  tracks = []
  for ti in spotofo.get_currently_playing_trackinfo(spotofo.get_users()):
    if spotofo.is_authorized_device(ti.username, ti.device):
      spotofo.analyze_play(ti)
      tracks.append(ti)
  track_uris = map(lambda x: x.uri, tracks)
  to_be_added_tracks = spotofo.deduplicate_tracks(track_uris)
  spotofo.add_tracks_to_playlist(to_be_added_tracks)
  return (tracks, track_uris, to_be_added_tracks)


def _oauth_authorize(username, scope=None, response=None):
  state, data = spotofo.authorize_with_scope(username, scope=scope)
  print('Please navigate here: %s' % data)
  response = raw_input('Enter the URL you were redirected to: ')
  state, data = spotofo.authorize_with_scope(username, scope=scope, response=response)
  return state, data


if __name__ == '__main__':
  cli()

