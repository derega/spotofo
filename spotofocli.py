
import os
import json
import click
import spotofo


@click.group()
@click.option('-c', 'cfn', help='Config file', default=os.path.expanduser('~/.spotofo.conf'))
@click.pass_context
def cli(ctx, cfn):
  ctx.obj = spotofo.get_config(cfn)


@cli.command()
@click.pass_context
def currently_playing(ctx):
  for trackinfo in spotofo.get_currently_playing_trackinfo(ctx.obj, spotofo.get_users(ctx.obj)):
    print trackinfo


@cli.command()
@click.pass_context
@click.argument('track')
def add_track(ctx, track):
  to_be_added_tracks = spotofo.deduplicate_tracks(ctx.obj, [track])
  spotofo.add_tracks_to_playlist(ctx.obj, to_be_added_tracks)


def _update_shared_playlist(ctx):
  tracks = []
  for ti in spotofo.get_currently_playing_trackinfo(ctx.obj, spotofo.get_users(ctx.obj)):
    if spotofo.is_authorized_device(ctx.obj, ti.username, ti.device):
      tracks.append(ti)
  track_uris = map(lambda x: x.uri, tracks)
  to_be_added_tracks = spotofo.deduplicate_tracks(ctx.obj, track_uris)
  spotofo.add_tracks_to_playlist(ctx.obj, to_be_added_tracks)
  return (tracks, track_uris, to_be_added_tracks)


def _mqtt_single(payload, host, port, topic, username=None, password=None):
  try:
    from paho.mqtt.publish import single
  except ImportError:
    print 'Install paho-mqtt'
    return
  auth = None
  if username and password:
    auth = {'username': username, 'password': password}
  kwargs = {
    'payload': payload,
    'qos': 0,
    'retain': False,
    'hostname': host,
    'port': int(port),
    'client_id': None,
    'keepalive': 60,
    'will': None,
    'auth': auth,
    'tls': None,
    'transport': 'tcp',
    }
  single(topic, **kwargs)


@cli.command()
@click.pass_context
def update_shared_playlist(ctx):
  tracks, track_uris, to_be_added_tracks = _update_shared_playlist(ctx)
  for ti in tracks:
    print ti, ti.uri in to_be_added_tracks


@cli.command()
@click.pass_context
@click.argument('host')
@click.argument('port')
@click.option('--topic', 'topic', help='Topic to subscribe', default='spotofo')
@click.option('--username', 'username', default=None)
@click.option('--password', 'password', default=None)
def mqtt(ctx, host, port, topic, username, password):
  tracks, track_uris, to_be_added_tracks = _update_shared_playlist(ctx)
  data = [x for x in tracks if x.uri in to_be_added_tracks]
  for ti in tracks:
    print ti
  if len(data):
    print repr(kwargs)
    _mqtt_single(json.dumps(data), host, port, topic, username, password)


@cli.command()
@click.pass_context
@click.argument('host')
@click.argument('port')
@click.argument('msg')
@click.option('--topic', 'topic', help='Topic to subscribe', default='spotofo')
@click.option('--username', 'username', default=None)
@click.option('--password', 'password', default=None)
def mqttsend(ctx, host, port, msg, topic, username, password):
  """Send message to MQTT topic"""
  _mqtt_single(msg, host, port, topic, username, password)


@cli.command()
@click.pass_context
@click.argument('host')
@click.argument('port')
@click.option('--topic', 'topic', help='Topic to subscribe', default='spotofo')
@click.option('--username', 'username', default=None)
@click.option('--password', 'password', default=None)
def mqttclient(ctx, host, port, topic, username, password):
  """This can be used to see what messages are sent to the topic"""
  try:
    import paho.mqtt.client as mqtt
  except ImportError:
    print 'Install paho-mqtt'
    return
  import json
  def on_connect(client, userdata, flags, rc):
    if rc == 0:
      client.subscribe(topic)
      print 'Subscribed:', repr(topic)
    else:
      print mqtt.error_string(rc)
  def on_message(client, userdata, msg):
    print(msg.topic+' '+repr(msg.payload))
  client = mqtt.Client()
  client.on_connect = on_connect
  client.on_message = on_message
  if username and password:
    client.username_pw_set(username, password)
  client.connect(host, int(port), 60)
  client.loop_forever()


@cli.command()
@click.argument('username')
@click.pass_context
def devices(ctx, username):
  devices = spotofo.get_user_devices(ctx.obj, username)
  for device in devices:
    print device['type'], repr(device['name']), 'ID:', device['id']


@cli.command()
@click.pass_context
def authorized(ctx):
  print 'Authorized to query data from user / device:'
  for username in spotofo.get_users(ctx.obj):
    for device in spotofo.get_devices(ctx.obj, username):
      print username, '/', device


@cli.command()
@click.argument('username')
@click.pass_context
def authorize_user(ctx, username):
  state, data = _oauth_authorize(ctx.obj, username, scope=spotofo.DEFAULT_SCOPE)
  if state == 'token' and data:
    spotofo.save_token_info(ctx.obj, username, data)
    devices = spotofo.get_user_devices(ctx.obj, username)
    device_ids = []
    for device in devices:
      print device['type'], repr(device['name']), 'ID:', device['id']
      device_ids.append(device['id'])
    device = raw_input('Enter the device ID you want to authorize: ')
    if device in device_ids:
      spotofo.add_user_device(ctx.obj, username, device)
      spotofo.save_config(ctx.obj)
      print 'Authorized to query data from user', username, 'device', device
    else:
      print "Can't authorize device", device
  else:
    print "Can't get token for", username


@cli.command()
@click.argument('target')
@click.pass_context
def authorize_playlist(ctx, target):
  username, playlist = spotofo.split_playlist(target)
  if not username:
    print 'Unable to handle playlist'
    return
  scope = 'playlist-modify-private'
  state, data = _oauth_authorize(ctx.obj, username, scope=scope)
  if state == 'token' and data:
    spotofo.save_token_info(ctx.obj, username, data)
    spotofo.save_playlist(ctx.obj, username, playlist)
    spotofo.save_config(ctx.obj)
    print 'Authorized to change playlist', target
  else:
    print "Can't get token for", username


def _oauth_authorize(config, username, scope=None, response=None):
  state, data = spotofo.authorize_with_scope(config, username, scope=scope)
  print('Please navigate here: %s' % data)
  response = raw_input('Enter the URL you were redirected to: ')
  state, data = spotofo.authorize_with_scope(config, username, scope=scope, response=response)
  return state, data


if __name__ == '__main__':
  cli()

