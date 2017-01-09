#!/usr/bin/env python

import spotipy
from spotipy import util
from spotipy.client import SpotifyException
import pprint
import pickle
import os
from collections import Counter
import re
import string
from spotify_tokens import * # stick your CLIENT_ID and CLIENT_SECRET here

SAVED_PATH = 'playlists.pickle'


RE_SPLIT_TOKENS = re.compile('[%s\s\\^\\\']' % re.escape(string.punctuation))


def tokenize(st):
  if not st:
    return []
  return [x for x in RE_SPLIT_TOKENS.split(st.lower()) if x]


def find_playlists(session, w):
  try:
    res = session.search(w, limit=50, type='playlist')
    while res:
      for playlist in res['playlists']['items']:
        yield playlist
      tries = 3
      while tries > 0:
        try:
          res = session.next(res['playlists'])
          tries = 0
        except SpotifyException as e:
          tries -= 1
          if tries == 0:
            raise
  except SpotifyException as e:
    status = e.http_status
    if status == 404:
      raise StopIteration
    raise


def main():
  word_counts = Counter()
  if os.path.isfile(SAVED_PATH):
    d = pickle.load(open(SAVED_PATH, 'rb'))
    words_seen = d['words_seen']
    playlists = d['playlists']
    if type(playlists) == list:
      playlists = {p['id']: p for p in playlists}
    for playlist in playlists.values():
      for token in tokenize(playlist['name']):
        word_counts[token] += 1
  else:
    words_seen = set()
    playlists = {}
    word_counts['a'] = 1

  token = util.prompt_for_user_token('DOsinga', '',
                                     client_id=CLIENT_ID, client_secret=CLIENT_SECRET,
                                     redirect_uri='http://127.0.0.1:8000/callback')
  session = spotipy.Spotify(auth=token)

  dupes = 0
  count = 0
  while True:
    for word, _ in word_counts.most_common():
      if not word in words_seen:
        words_seen.add(word)
        print('word>', word)
        for playlist in find_playlists(session, word):
          if playlist['id'] in playlists:
            dupes += 1
          else:
            playlists[playlist['id']] = {
              'owner': playlist['owner']['id'],
              'name': playlist['name'],
              'id': playlist['id'],
            }
          count += 1
          for token in tokenize(playlist['name']):
            word_counts[token] += 1
          if len(playlists) % 1000 == 0:
            print('..', len(playlists), count, dupes)
        with open(SAVED_PATH, 'wb') as fout:
          pickle.dump({'words_seen': words_seen,
                       'playlists': playlists}, fout, -1)
        break
    else:
      return


if __name__ == '__main__':
  main()





