#!/usr/bin/python3
# Purpose: Fetch Clementine playing song lyrics (Greek) from stixoi.info
# Author:  Dimitrios Glentadakis <dglent@free.fr>
# License: GPLv3

from bs4 import BeautifulSoup
import re
import urllib.request
import dbus


class Stixoi():
    def __init__(self):
        self.header = {'User-Agent': 'Mozilla/5.0 (X11; Linux)'}
        self.lyrics_prefix = ('http://www.stixoi.info/stixoi.php?info='
                              'Lyrics&act=details&song_id=')
        self.url_prefix = 'http://www.stixoi.info/stixoi.php?info=SS&keywords='
        self.url_suffix = '&act=ss'
        self.songs_dic = {}
        track_playiyng = self.now_playing()
        self.search_times = 0
        self.search_parser(track_playiyng)
        list_found_songs = []
        relevance_list = []
        for key, val in self.songs_dic.items():
            if int(val[0][:-1]) >= 95:
                relevance_list.append(int(val[0][:-1]))
                list_found_songs.append(key)
        relevance_list.sort()
        show_once = []
        for percent in relevance_list:
            for key, val in self.songs_dic.items():
                if percent == int(val[0][:-1]):
                    if key not in show_once:
                        self.list_search_results(key)
                        show_once.append(key)
        if len(list_found_songs) == 1:
            self.lyrics_parser(list_found_songs[0])
        elif len(list_found_songs) > 1:
            print('Σύνολο: ', len(list_found_songs))
            song_id = input('Εισαγάγετε το αναγνωριστικό τραγουδιού:\n')
            for i in list_found_songs:
                if i == song_id:
                    print('__________________\n')
                    print(self.songs_dic[i][1])
                    print('__________________')
                    self.lyrics_parser(i)
                    break
        else:
            print('Ουδέν αποτέλεσμα')

    def lyrics_parser(self, song_id):
        lyrics = ''
        req = urllib.request.Request(
            self.lyrics_prefix + song_id, headers=self.header
        )
        for word in urllib.request.urlopen(req).readlines():
            lyrics += word.strip().decode('utf-8')
            lyrics = lyrics.replace('<br />', '\n')
        soup = BeautifulSoup(lyrics, 'lxml')
        td = soup.find_all('td')
        logia = str(td[0]).replace('<br/>', '\n').split('</td></tr>')
        print('\n')
        for i in logia:
            if i.count('</table></div>'):
                # remove advertisement string at the last 50 characters
                print((re.sub('<[^>]*>', '', i)).strip()[:-50])
                print('Url: ' + self.lyrics_prefix + song_id)
                break

    def now_playing(self):
        bus = dbus.SessionBus()
        try:
            proxy = bus.get_object(
                'org.mpris.MediaPlayer2.clementine', '/org/mpris/MediaPlayer2'
            )
        except dbus.exceptions.DBusException:
            proxy = bus.get_object(
                'org.mpris.MediaPlayer2.strawberry', '/org/mpris/MediaPlayer2'
            )
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

        return self.title + '+' + self.artist

    def search_songs(self, track_playing):
        title = track_playing.replace("'", " ")
        string_to_search = (repr(title.encode('utf-8')).replace("b'", "").
                            replace("\\x", "%").replace("'", "").
                            replace(' ', '+'))
        search_results_html = ''
        req = urllib.request.Request(
            self.url_prefix + string_to_search + self.url_suffix,
            headers=self.header
        )
        for word in urllib.request.urlopen(req).readlines():
            search_results_html += word.strip().decode('utf-8')
        return search_results_html

    def search_parser(self, track_playiyng):
        search_results_html = self.search_songs(track_playiyng)
        html_soup = BeautifulSoup(search_results_html, 'lxml')
        lista = html_soup.find_all('center')[2]
        counter = 0
        relevance = ''
        song_id = ""
        self.songs_dic = {}
        for i in lista.find_all('td'):
            val = i.get_text()
            if val == '':
                val = '-'
            if len(val) >= 2 and val.count('%') == 1:
                relevance = val
                counter += 1
                continue
            if counter == 1:
                song_id = re.search("song_id=([0-9]+)", str(i)).group(1)
                self.songs_dic[song_id] = []
                self.songs_dic[song_id].append(relevance)
                self.songs_dic[song_id].append(val)
                counter += 1
                continue
            if counter == 2:
                self.songs_dic[song_id].append(val)
                counter += 1
                continue
            if counter == 3:
                self.songs_dic[song_id].append(val)
                counter += 1
                continue
            if counter == 4:
                self.songs_dic[song_id].append(val)
                counter += 1
                continue
            if counter == 5:
                self.songs_dic[song_id].append(val)
                counter = 0
        # If cannot find with title + artist try only with title
        if len(self.songs_dic) == 0 and self.search_times == 0:
            self.search_times = 1
            self.search_parser('"' + self.title + '"')

    def list_search_results(self, song):
        for key, val in self.songs_dic.items():
            if key == song:
                print('__________________\n')
                print('Τραγούδι:    ', key, ': "' + val[1][1:] + '",', val[0])
                print('Στιχουργός:  ', val[2])
                print('Συνθέτης:    ', val[3])
                print('1η εκτέλεση: ', val[4])
                print('Έτος:        ', val[5])


if __name__ == '__main__':
    app = Stixoi()
