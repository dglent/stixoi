#!/usr/bin/python

from bs4 import BeautifulSoup
import re
import requests
import dbus
import sys
from operator import itemgetter


class Stixoi():
    def __init__(self):
        self.session = requests.Session()
        user_agent = 'Mozilla/5.0 (X11; Linux)'
        self.session.headers.update({'user-agent': user_agent})
        self.url = 'https://www.greekstixoi.gr/?s='
        self.now_playing()
        self.search_parser()

    def get_proxy(self, bus, player):
        try:
            proxy = bus.get_object(
                f'org.mpris.MediaPlayer2.{player}', '/org/mpris/MediaPlayer2'
            )
            return proxy
        except dbus.exceptions.DBusException:
            return False

    def now_playing(self):
        self.title = ''
        self.artist = ''
        self.album = ''
        self.year = ''
        bus = dbus.SessionBus()
        for player in ['clementine', 'strawberry', 'sayonara']:
            proxy = self.get_proxy(bus, player)
            if proxy:
                break

        properties_manager = dbus.Interface(
            proxy, 'org.freedesktop.DBus.Properties'
        )
        metadata = properties_manager.Get(
            'org.mpris.MediaPlayer2.Player', 'Metadata'
        )

        self.artist = str(metadata.get('xesam:artist')[0])
        self.title = str(metadata.get('xesam:title'))
        self.album = str(metadata.get('xesam:album'))
        self.year = str(metadata.get('year'))

    def search_songs(self):
        string_to_search = ''
        search_results_html = ''
        for i in self.title:
            gramma = repr(i.encode('utf-8'))
            gramma = gramma.replace('''b"'"''', '%27')
            gramma = gramma.replace("b'", "", 1)
            gramma = gramma.replace("\\x", "%")
            gramma = gramma.replace("'", "")
            gramma = gramma.replace(' ', '+')
            string_to_search += gramma
        print('--------------------------------')
        print(f'| Τίτλος: {self.title}')
        print(f'| Καλλιτέχνης: {self.artist}')
        print(f'| Δίσκος: {self.album}')
        print(f'| Έτος: {self.year}')
        print('---------------------------------')
        url = f'{self.url}{self.title}'
        print('URL αναζήτησης: ', f'{self.url}{string_to_search}')
        html = self.get_html(url)
        return html

    def get_html(self, url):
        req = self.session.get(url, timeout=10)
        if req.status_code != 200:
            print(f'Error: {req.status_code}')
            return False
        else:
            return req.text

    def search_parser(self):
        search_results_html = self.search_songs()
        if not search_results_html:
            return
        html_soup = BeautifulSoup(search_results_html, 'lxml')
        songs = html_soup.find_all('article')

        song_url = ''
        self.results = {}
        counter = 0
        for entry in songs:
            counter += 1
            track = entry.find("h2", 'post-title entry-title')
            title_year = track.text.split('–')
            if len(title_year) == 1:
                title_year.insert(1, '')
            artist = entry.find("p", "post-tag")
            if artist is None:
                artist = ''
            else:
                artist = artist.text.replace('Καλλιτέχνης:', '')
            album = entry.find("p", "post-album")
            if album is None:
                album = ''
            else:
                album = album.text.replace('Album:', '')
            self.results[counter] = {
                'song': title_year[0],
                'artist': artist.strip(),
                'playing_artist_keywords': self.artist.strip().split(' '),
                'album': album.strip(),
                'year': title_year[1].strip(),
                'url': track.a['href'],
                'score': 0,
            }
        if counter == 0:
            print('Ουδέν αποτέλεσμα')
            return
        for i in self.results:
            if i < 5:
                self.results[i]['score'] += 1
            song_keys = [self.remove_accents(s.lower()) for s in self.results[i]['song'].split(' ')]
            playing_song_keys = [self.remove_accents(s.lower()) for s in self.title.split(' ')]
            for key in playing_song_keys:
                if key in song_keys:
                    self.results[i]['score'] += 1
            if self.year == self.results[i]['year']:
                self.results[i]['score'] += 1
            for key in self.results[i]['playing_artist_keywords']:
                if key in self.results[i]['artist'].split(' '):
                    self.results[i]['score'] += 1

        self.score_results = sorted(self.results.values(), key=itemgetter('score'))

        url = self.score_results[-1]['url']
        html_lyrics = self.get_html(url)
        html_lyrics = BeautifulSoup(html_lyrics, 'lxml')
        print('\n======== ΑΠΟΤΕΛΕΣΜΑ ΑΝΑΖΗΤΗΣΗΣ ==========')
        print(f"|{html_lyrics.find('div', 'h2title').text}")
        print(f"|Καλλιτέχνης: {self.score_results[-1]['artist']}")
        print(f"|Δίσκος: {self.score_results[-1]['album']}")
        print('--------------------------------------\n')
        print(html_lyrics.find('div', 'lyrics').text)
        print(f'\nURL κομματιού: {url}')

    def remove_accents(self, word):
        accents = {
            "ά": "α",
            "έ": "ε",
            "ύ": "υ",
            "ί": "ι",
            "ό": "ο",
            "ή": "η",
            "ώ": "ω",
        }
        new_word = ''
        for gramma in word:
            new_word += accents.get(gramma, gramma)

        return new_word


if __name__ == '__main__':
    app = Stixoi()
