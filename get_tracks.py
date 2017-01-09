#!/usr/bin/env python
import multiprocessing
import sys

import spotipy
from spotipy import util
from spotipy.client import SpotifyException
import pickle
import os
import time
from spotify_tokens import * # stick your CLIENT_ID and CLIENT_SECRET here

# PLAYLIST_PATH = 'playlists.pickle'
TRACKS_PATH = 'tracks.pickle'

paused = False

def track_yielder(session, owner_id, playlist_id):
  try:
    res = session.user_playlist_tracks(owner_id, playlist_id,
                                fields='items(track(id, name, artists(name, id), duration_ms)),next')
    while res:
      for track in res['items']:
        yield track['track']
      tries = 3
      while tries > 0:
        try:
          res = session.next(res)
          if not res or  not res.get('items'):
            raise StopIteration
          for track in res['items']:
            yield track['track']
          tries = 0
        except SpotifyException as e:
          if 400 <= e.http_status <= 499:
            raise StopIteration
          tries -= 1
          time.sleep(1)
          if tries == 0:
            raise e
  except SpotifyException as e:
    if 400 <= e.http_status <= 499:
      raise StopIteration
    raise e


def fetch_playlists(session, control_queue, result_queue):
  while not control_queue.empty():
    while paused:
      time.sleep(0.1)
    playlist = control_queue.get()
    tracks = list(track_yielder(session, playlist['owner'], playlist['id']))
    result_queue.put((playlist['id'], tracks))


def main():
  global paused
  d = pickle.load(open(PLAYLIST_PATH, 'rb'))
  playlists = list(d['playlists'].values())
  print('Loaded %d playlists' % len(playlists))
  del d
  track_count = 0
  if os.path.isfile(TRACKS_PATH):
    tracks, track_ids_in_playlists = pickle.load(open(TRACKS_PATH, 'rb'))
    track_count = sum(track['count'] for track in tracks.values())
    print('Loaded %d playlists with %d tracks (%d unique)' % (len(track_ids_in_playlists), track_count, len(tracks)))
  else:
    tracks = {}
    track_ids_in_playlists = {}

  while True:
    print('Getting Auth')
    token = util.prompt_for_user_token('DOsinga', '',
                                       client_id=CLIENT_ID, client_secret=CLIENT_SECRET,
                                       redirect_uri='http://127.0.0.1:8000/callback')
    session = spotipy.Spotify(auth=token)

    control_queue = multiprocessing.Queue()
    result_queue = multiprocessing.Queue()
    for playlist in playlists:
      if not playlist['id'] in track_ids_in_playlists:
        control_queue.put(playlist)

    if control_queue.empty():
      break
    processes = []
    for task_idx in range(3):
      p = multiprocessing.Process(target=fetch_playlists, args=(session, control_queue, result_queue))
      p.start()
      processes.append(p)

    fetched = 0
    missed_count = 0
    start = time.time()
    while any(p.is_alive() for p in processes):
      while not result_queue.empty():
        playlist_id, tracks_in_playlist = result_queue.get()
        tracks_in_playlist = [t for t in tracks_in_playlist if t]
        if tracks_in_playlist:
          track_count += len(tracks_in_playlist)
          for track in tracks_in_playlist:
            track = tracks.setdefault(track['id'], track)
            track['count'] = track.get('count', 0) + 1
          track_ids_in_playlists[playlist_id] = [track['id'] for track in tracks_in_playlist]
          fetched += 1
          missed_count = 0
        else:
          missed_count += 1
          if missed_count == 20:
            paused = True
            print('pausing for 30m after %d misses, then exiting' % missed_count)
            for p in processes:
              p.terminate()
            time.sleep(1800)
            sys.exit()

        if len(track_ids_in_playlists) % 100 == 0:
          print('playlists: %d (%2.1f%%) - qps: %2.1f - tracks: %d' % (len(track_ids_in_playlists), len(track_ids_in_playlists) * 100 / len(playlists), fetched / (time.time() - start), track_count))
          if os.path.isfile(TRACKS_PATH):
            os.rename(TRACKS_PATH, TRACKS_PATH + '.tmp')
          with open(TRACKS_PATH, 'wb') as fout:
            pickle.dump((tracks, track_ids_in_playlists), fout, -1)
          if os.path.isfile(TRACKS_PATH + '.tmp'):
            os.remove(TRACKS_PATH + '.tmp')
        if len(track_ids_in_playlists) % 5000 == 0:
          paused = True
          print('Taking a break to quiet things down (20m)')
          time.sleep(1200)
          print('Break is done.')
          paused = False
      time.sleep(0.1)
    with open(TRACKS_PATH, 'wb') as fout:
      pickle.dump((tracks, track_ids_in_playlists), fout, -1)

if __name__ == '__main__':
  main()





