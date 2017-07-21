
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

  $ spotofo authorize username
  $ spotofo currently_playing

By default the script uses ~/.spotofo.conf to store its config.
Run authorize once and then fill in the blanks in the config file.

