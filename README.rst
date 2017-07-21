
Tool for Spotify
****************

Do fun things with Spotify.

Installation
============

Create virtualenv and install our stuff::

  $ virtualenv venv
  $ . venv/bin/activate
  $ pip install --editable .

Do fun things::

  $ spotofo authorize <username>
  $ vim ~/.spotofo.conf
  $ spotofo authorize <username>
  $ spotofo authorized
  $ spotofo currently_playing
  $ spotofo playlist spotify:user:<username>:playlist:<id>
  $ spotofo update_shared_playlist

By default the script uses ~/.spotofo.conf to store its config.
Run authorize once and then fill in the blanks in the config file.

