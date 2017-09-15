
from setuptools import setup

setup(
    name='spotofo',
    version='0.1',
    py_modules=['spotofo', 'spotofocli', 'spotofoweb'],
    install_requires=[
        'Click==6.7',
        'spotipy>=2.4.4',
        'django==1.11',
        'django-bootstrap-form==3.3',
        'unicodecsv==0.14.1',
        'dj-database-url==0.4.2',
    ],
    extras_require={
        'mqtt': ['paho-mqtt==1.3.0'],
        'influx': ['requests==2.18.2'],
    },
    entry_points={
        'console_scripts': [
            'spotofo=spotofocli:cli',
        ],
    },
)
