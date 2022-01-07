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

        try:
            self.artist = str(metadata.get('xesam:artist')[0])
        except TypeError:
            self.artist = ''
        self.title = str(metadata.get('xesam:title'))
        self.album = str(metadata.get('xesam:album'))
        self.year = str(metadata.get('year'))

    def search_songs(self):
        string_to_search = ''
        search_results_html = ''
        for i in self.title:
            i = i.replace("'", " ")  # replace apostrophe with space
            gramma = repr(i.encode('utf-8'))
            gramma = gramma.replace('''b"'"''', '%27')
            gramma = gramma.replace("b'", "", 1)
            gramma = gramma.replace("\\x", "%")
            gramma = gramma.replace("'", "")
            gramma = gramma.replace(' ', '+')
            gramma = gramma.replace('(', '')
            gramma = gramma.replace(')', '')

            string_to_search += gramma
        print('--------------------------------')
        print(f'| Τίτλος: {self.title}')
        print(f'| Καλλιτέχνης: {self.artist}')
        print(f'| Δίσκος: {self.album}')
        print(f'| Έτος: {self.year}')
        print('---------------------------------')
        search_string_url = self.title
        search_string_url = search_string_url.replace("'", "+")  # replace apostrophe with +
        search_string_url = search_string_url.replace('(', '')
        search_string_url = search_string_url.replace(')', '')
        url = self.url + search_string_url
        print('URL αναζήτησης: ', f'{self.url}{string_to_search}')
        self.songs = []
        html = self.get_html(url)
        html = self.find_songs_in_page(html)
        navigation = html.find_all("div", "pagenav tf_clear tf_box tf_textr tf_clearfix")
        if len(navigation) > 0:
            pages = navigation[0]
            for page in pages.find_all("a", "number"):
                if page.text in ['2', '3', '4']:
                    url_next = page.get('href')
                    html = self.get_html(url_next)
                    self.find_songs_in_page(html)

    def find_songs_in_page(self, html):
        html = BeautifulSoup(html, 'lxml')
        songs = html.find_all('article')
        for song in songs:
            self.songs.append(song)
        return html

    def get_html(self, url):
        req = self.session.get(url, timeout=10)
        if req.status_code != 200:
            print(f'Error: {req.status_code}')
            return False
        else:
            return req.text

    def search_parser(self):
        self.search_songs()
        if len(self.songs) == 0:
            return

        song_url = ''
        results = {}
        counter = 0
        for entry in self.songs:
            year = ''
            song_title = ''
            counter += 1
            track = entry.find("h2", 'post-title entry-title')
            if track.text.count('–'):
                title_year = track.text.split('–')
            else:
                title_year = track.text.split('-')
            song_title = title_year[0].strip()
            if len(title_year) > 1:
                # After the dash is the year
                year = title_year[1].strip()
                if not year.isnumeric():
                    # After the dash is part of the song title
                    song_title += ' ' + year
                    year = ''
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
            song_title = song_title.replace('-', ' ')
            results[counter] = {
                'song': song_title.strip(),
                'artist': artist.strip(),
                'playing_artist_keywords': self.artist.strip().split(' '),
                'album': album.strip(),
                'year': year,
                'url': track.a['href'],
                'score': 0,
            }
        if counter == 0:
            print('Ουδέν αποτέλεσμα')
            return
        for i in results:
            if i < 5:
                results[i]['score'] += 1
            song_keys = [self.remove_accents(s.lower()) for s in results[i]['song'].split(' ')]
            playing_song_keys = [self.remove_accents(s.lower()) for s in self.title.split(' ')]
            album_keys = [self.remove_accents(s.lower()) for s in results[i]['album'].split(' ')]
            playing_album_keys = [
                self.remove_accents(s.lower().replace('-', ' ')) for s in self.album.split(' ')
            ]
            for key in playing_song_keys:
                if key in song_keys:
                    results[i]['score'] += 1
            for key in playing_album_keys:
                if key in album_keys:
                    results[i]['score'] += 1
            if (
                self.remove_accents(self.title.lower().strip())
                == self.remove_accents(results[i]['song'].lower().strip())
            ):
                results[i]['score'] += 2
            if (
                self.remove_accents(self.album.lower().strip())
                == self.remove_accents(results[i]['album'].lower().strip())
            ):
                results[i]['score'] += 2
            if self.year == results[i]['year']:
                results[i]['score'] += 2
            for key in results[i]['playing_artist_keywords']:
                if key in results[i]['artist'].split(' '):
                    results[i]['score'] += 1

        score_results = sorted(results.values(), key=itemgetter('score'))

        url = score_results[-1]['url']
        html_lyrics = self.get_html(url)
        html_lyrics = BeautifulSoup(html_lyrics, 'lxml')
        details = html_lyrics.find('div', 'details')
        det = details.find_all(rel="tag")
        try:
            stixourgos = [i.text for i in det if str(i).count("stixourgos")][0]
        except IndexError:
            stixourgos = ''
        try:
            synthetis = [i.text for i in det if str(i).count("synthetis")][0]
        except IndexError:
            synthetis = ''
        print(f"\n=== ΑΠΟΤΕΛΕΣΜΑ ΑΝΑΖΗΤΗΣΗΣ - ΒΑΘΜΟΣ: {score_results[-1]['score']} ===")
        print(f"|{html_lyrics.find('div', 'h2title').text}")
        print(f"|Καλλιτέχνης: {score_results[-1]['artist']}")
        print(f"|Στιχουργός: {stixourgos}")
        print(f"|Συνθέτης: {synthetis}")
        print(f"|Δίσκος: {score_results[-1]['album']}")
        print('--------------------------------------\n')
        print(html_lyrics.find('div', 'lyrics').text)
        print(f'\nURL κομματιού: {url}')


    def remove_accents(self, word):
        accents = {
            "ά": "α",
            "έ": "ε",
            "ύ": "υ",
            "ί": "ι",
            "ϊ": "ι",
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
