
Tool for Spotify
****************

Do fun things with Spotify.

Installation
============

Create virtualenv and install our stuff::

  $ virtualenv venv
  $ . venv/bin/activate
  $ pip install --editable .

If you want to use the MQTT stuff you need to install the package with::

  $ pip install --editable ".[mqtt]"

Do fun things::

  $ spotofo authorize_user <username>
  $ vim ~/.spotofo.conf
  $ spotofo authorize_user <username>
  $ spotofo authorized
  $ spotofo currently_playing
  $ spotofo authorize_playlist spotify:user:<username>:playlist:<id>
  $ spotofo update_shared_playlist

By default the script uses ~/.spotofo.conf to store its config.
Run authorize once and then fill in the blanks in the config file.

Run update_shared_playlist in a cronjob to automatically sync
currently playing track to the playlist.

