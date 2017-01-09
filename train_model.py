#!/usr/bin/env python
import pickle
from collections import Counter
import sys
import gensim, logging
import multiprocessing

logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s', level=logging.INFO)


TRACKS_PATH = 'tracks.pickle'
MODEL_PATH = 'songs.model'

def divese_playlist(tracks, playlist):
  if not playlist:
    return False
  c = Counter(tracks[t]['artists'][0]['id'] for t in playlist)
  if c.most_common(1)[0][1] * 2 > sum(c.values()):
    return False
  return True

def main():
  print('loading tracks')
  tracks, track_ids_in_playlists = pickle.load(open(TRACKS_PATH, 'rb'))
  print('got %d playlists' % (len(track_ids_in_playlists)))
  track_ids_in_playlists = [list(filter(None, x)) for x in track_ids_in_playlists.values() if len(x) < 120 and len(x) > 0]
  print('down %d after filtering long ones' % len(track_ids_in_playlists))
  track_ids_in_playlists = [playlist for playlist in track_ids_in_playlists if divese_playlist(tracks, playlist)]
  print('down %d after filtering diversity' % len(track_ids_in_playlists))
  num_songs = sum(len(x) for x in track_ids_in_playlists)
  print('%d playlist with %d songs' % (len(track_ids_in_playlists), num_songs))

  model = gensim.models.Word2Vec(iter=1,
                                 workers=multiprocessing.cpu_count(),
                                 window=10,
                                 min_count=4,
                                 size=30)
  model.build_vocab(track_ids_in_playlists)
  for i in range(50):
    model.train(track_ids_in_playlists)
  model.save(MODEL_PATH)

if __name__ == '__main__':
  main()
