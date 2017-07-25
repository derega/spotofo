
from setuptools import setup

setup(
    name='spotofo',
    version='0.1',
    py_modules=['spotofo', 'spotofocli'],
    install_requires=[
        'Click==6.7',
        'spotipy==2.4.4',
    ],
    extras_require={
        'mqtt': ['paho-mqtt==1.3.0'],
    },
    entry_points={
        'console_scripts': [
            'spotofo=spotofocli:cli',
        ],
    },
)
