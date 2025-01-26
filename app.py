import os
import time
import yt_dlp
import ffmpeg
import random
import spotipy
from io import BytesIO
from pygame import mixer 
from pprint import pprint
from datetime import datetime
from pydub import AudioSegment 
from ytmusicapi import YTMusic
from spotipy.oauth2 import SpotifyClientCredentials

CLIENT_ID = "3a37e2adaf224237b96d901fd80b1829"
CLIENT_SECRET = "1c58b4a6904f451b8a205472a2a18f0e"
ytmusic = YTMusic('oauth.json') 

with open('genres.txt', 'r') as f:
    genres = f.read().split('\n')

def get_random_song(genre=None, start_year=None, end_year=None):
    duration = 1000
    while duration > 600:
        if not genre:
            genre = genres[random.randint(0,len(genres)-1)]
        if not end_year:
            datetime.now().year
        if not start_year:
            parameters = f"genre:{genre}"
        else:
            parameters = f"genre:{genre} year:{start_year}-{end_year}"

        creds = SpotifyClientCredentials(client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
        sp = spotipy.Spotify(client_credentials_manager=creds)

        num_results = sp.search(q=parameters, type="track", limit=1)['tracks']['total']
        results = sp.search(q=parameters, type="track", limit=1, offset=random.randint(0,num_results-1))

        artist = results['tracks']['items'][0]['album']['artists'][0]['name']
        title = results['tracks']['items'][0]['name']
        popularity = results['tracks']['items'][0]['popularity']
        query = f'{title} by {artist}'
        cover = results['tracks']['items'][0]['album']['images'][0]['url']
        release_date = results['tracks']['items'][0]['album']['release_date']
        album_name = results['tracks']['items'][0]['album']['name']
        
        search_results = ytmusic.search(query, filter='songs', limit=1)
        id = search_results[0]['videoId']
        duration = search_results[0]['duration_seconds']

    return query, id, duration, cover, genre, release_date, album_name, start_year, end_year, title, artist, popularity

def download_song(id, start):
    output_dir = 'static/clips'
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
        'external_downloader': 'ffmpeg',
        'external_downloader_args': [
            '-ss', str(start), '-t', '5'  # Start time and duration
        ],
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(f'https://www.youtube.com/watch?v={id}', download=True)

    filename = ydl.prepare_filename(info_dict)
    return filename.replace('.webm','.mp3')


## Flask App

from flask import jsonify, Flask, Response, render_template, send_file, stream_with_context, request, session, redirect, url_for
from threading import Thread
import time

download_progress = {}

app = Flask(__name__)
app.secret_key = 'blue-swan'

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/dig', methods=['POST'])
def dig():
    params = request.get_json()  
    genre = params.get('genre')
    start_year = params.get('startYear')
    end_year = params.get('endYear')
    is_test = params.get('isTest')

    if is_test:
        url = 'https://www.youtube.com/watch?v=RLBgQrvAp6Q'
        query = 'Only One (feat. DJ Spinn & Taso) by DJ Rashad'
        id = 'RLBgQrvAp6Q'
        duration = 225 
        cover = 'https://i.scdn.co/image/ab67616d0000b273555c5ca872b9e20971920513'
        genre = 'Footwork' 
        release_date = '2013-01-01'
        album_name = 'Double Cup'
        start_year = None
        end_year = None
        title = 'Only One (feat. DJ Spinn & Taso)'
        artist = 'DJ Rashad'
        popularity = 18
    else:
        try:
            query, id, duration, cover, genre, release_date, album_name, start_year, end_year, title, artist, popularity = get_random_song(genre, start_year, end_year)
            url = f'https://www.youtube.com/watch?v={id}'
        except ValueError:
            return jsonify({'status': 'error', 'message': 'NO TRACKS FOUND'})
        except:
            return jsonify({'status': 'error', 'message': 'TRY AGAIN'})

    return jsonify({'status': 'success',
                    'id': id, 
                    'url': url,
                    'query': query, 
                    'title': title,
                    'artist': artist,
                    'cover': cover, 
                    'duration': duration, 
                    'genre': genre,
                    'release_date': release_date,
                    'album_name': album_name,
                    'start_year': start_year,
                    'end_year': end_year,
                    'popularity': popularity})

@app.route('/drop', methods=['POST'])
def drop():
    params = request.get_json()
    id = params.get('id')
    duration = params.get('duration')
    start_time = random.randint(0,duration-5)
    is_test = params.get('isTest')

    if is_test:
        path = 'static/clips/Only One (feat. DJ Spinn & Taso).mp3'
    else:
        path = download_song(id, start_time)
        
    return jsonify({'path':path,'start_time':start_time})

@app.route('/cleanup', methods=['POST'])
def cleanup():
    params = request.get_json()
    path = params.get('path')
    is_test = params.get('isTest')
    if os.path.exists(path) and not is_test:
        os.remove(path)
    return jsonify({'status': 'deleted'})

if __name__ == '__main__':
    app.run(debug=True)