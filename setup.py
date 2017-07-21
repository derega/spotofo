
from setuptools import setup

setup(
    name='spotofo',
    version='0.1',
    py_modules=['spotofo'],
    install_requires=[
        'Click==6.7',
        'spotipy==2.4.4',
    ],
    entry_points='''
        [console_scripts]
        spotofo=spotofo:main
    ''',
)
