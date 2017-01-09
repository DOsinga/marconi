#!/usr/bin/env python
import pickle
from collections import Counter
import re
import string
import gensim, logging
import multiprocessing

logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s', level=logging.INFO)


MODEL_PATH = 'songs.model'
TRACKS_INFO_PATH = 'tracks-info.pickle'

def main():
  songs = pickle.load(open(TRACKS_INFO_PATH, 'rb'))
  model = gensim.models.Word2Vec.load(MODEL_PATH)
  for song_id, score in model.most_similar(positive=['2z0vATajOBlmLnOMErZWZD'], topn=25):
    print(song_id[1:] if song_id.startswith('*') else songs[song_id], score)

if __name__ == '__main__':
  main()
