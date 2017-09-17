
Tool for Spotify
****************

Do fun things with Spotify. Currently playing information! Play history!

The app can be run from CLI or as a Django web service in Heroku.

Dependencies
============

Django is required in all operating modes as data storage uses Django ORM.
Database can be SQLite or Postgres, also MySQL might work.

Memcached is good to have, otherwise data is queried from Spotify API
on every request.

::

  Usage: spotofo [OPTIONS] COMMAND [ARGS]...

  Options:
    -c TEXT  Config file
    --help   Show this message and exit.

  Commands:
    add_track           Add track to playlist
    authorize_device    Add new device
    authorize_playlist  Change target playlist
    authorize_user      Add new user
    authorized          List authorized users and devices
    config              Show config
    currently_playing   Currently playing tracks for all users
    devices             List available devices for user
    mqtt_client         Monitor MQTT topic for messages
    mqtt_config         Set MQTT connection parameters
    mqtt_send           Send message to MQTT topic
    update_playlist     Add currently playing tracks to the playlist...


Installation
============

Create virtualenv and install our stuff::

  $ virtualenv venv
  $ . venv/bin/activate
  $ pip install -r requirements.txt

If you want to use the MQTT stuff you need to install the package with::

  $ pip install --editable ".[mqtt]"

Do fun things::

  $ spotofo authorize_user <username>
  $ spotofo authorized
  $ spotofo currently_playing
  $ spotofo authorize_playlist spotify:user:<username>:playlist:<id>
  $ spotofo update_playlist

Run update_playlist in a cronjob to automatically sync playing history and
currently playing track to the playlist.


Deploy to Heroku
================

* Create Heroku app
* Add Postgres addon
* Add Sentry addon
* Add Heroku Lab Dyno Metadata addon
* Enable SSL
* Register Spotify App, to get API tokens
* Add env vars to the app
* Push the contents of this repo to Heroku
* Run migrate for the database
* Authenticate yourself from web UI
* Activate at least one device from web UI
* Authenticate one playlist from CLI
* Listen to music :)

Needed env vars in Heroku::

  DJANGO_SETTINGS_MODULE='spotofoweb.heroku'
  SECRET_KEY='<generate random string>'
  SPOTOFO_CLIENT_ID='<you get this from Spotify>'
  SPOTOFO_CLIENT_SECRET='<you get this from Spotify>'
  SPOTOFO_REDIRECT_URI='<domain of your choice>/authorize/response'


Run update_playlist on your own machine
---------------------------------------

Because you are cheap hobby dev you don't want to pay
for second dyno you run the cronjob on your own machine locally.

Sure, you could put it to Heroku Scheduler and run every ten minutes.
But then you would miss songs which are less than ten minutes long.
Not good.

This is also handy while developing as you can use the same database
and Spotify credentials, so not only because you are cheap ;)

First we get env vars from Heroku to our local env::

  heroku config -s > .env

Then we create local_settings.py file with following contents::

  import os
  BASE_DIR = os.path.dirname(os.path.abspath(__file__))

  from dotenv import load_dotenv
  load_dotenv(os.path.join(BASE_DIR, '.env'))

  from spotofoweb.heroku import *

  SPOTOFO_REDIRECT_URI='<insert your domain here>/authorize/response/playlist'

Last item in our checklist is to add the second redirect URI we just came up with
to Spotify app in Spotify admin panel so we can authenticate stuff from CLI
without the web app catching redirects coming from Spotify.

Now we can run stuff happily from CLI::

  DJANGO_SETTINGS_MODULE=local_settings spotofo update_playlist


