import os
import uuid
import json
import time
import shlex
import yt_dlp
import ffmpeg
import random
import spotipy
import requests
import platform
import tempfile
from io import BytesIO
from datetime import datetime
from ytmusicapi import YTMusic
from spotipy.oauth2 import SpotifyClientCredentials
from flask import jsonify, Flask, abort, Response, render_template, send_file, stream_with_context, request, session, redirect, url_for, stream_with_context
from subprocess import Popen, PIPE, run

with open('spotify.json','r') as f:
    spotify_credentials = json.load(f)

CLIENT_ID = spotify_credentials['CLIENT_ID']
CLIENT_SECRET = spotify_credentials['CLIENT_SECRET']
ytmusic = YTMusic('oauth.json') 

with open('genres.txt', 'r') as f:
    genres = f.read().split('\n')

def search_deezer_track(query, limit=1):
    url = f"https://api.deezer.com/search?q={query}&limit={limit}"
    res = requests.get(url)
    data = dict(res.json()['data'][0])
    to_return = {
        "title": data["title"],
        "artist": data["artist"]["name"],
        "id": data["id"],
        "url": data["link"],
        "preview": data["preview"]
    }
    return to_return

def get_random_song(genre=None, start_year=None, end_year=None, artist=None, album=None, track=None):

    song_found = False
    while song_found == False:
        parameters = ''
        if genre:
            parameters += f"genre:{genre} "
        else:
            genre = genres[random.randint(0,len(genres)-1)]
            parameters += f"genre:{genre} "
        
        if start_year and end_year:
            parameters += f" year:{start_year}-{end_year} "

        if artist:
            parameters = f'artist:{artist}'
        elif album:
            parameters = f'artist:{artist} album:{album}'

        creds = SpotifyClientCredentials(client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
        sp = spotipy.Spotify(client_credentials_manager=creds)

        if artist or album:
            retry = 0
            found = False
            while (found == False) and (retry < 4):
                num_results = sp.search(q=parameters, type="track", limit=1)['tracks']['total']
                spotify_results = sp.search(q=parameters, type="track", limit=1, offset=random.randint(0,num_results-1))
                title = spotify_results['tracks']['items'][0]['name']
                artist_name = spotify_results['tracks']['items'][0]['album']['artists'][0]['name']
                album_name = spotify_results['tracks']['items'][0]['album']['name']

                if album and (title != track) and (artist_name == artist) and (album_name == album):
                    print(album)
                    print(album_name)
                    found = True
                if not album and artist and (title != track) and (artist_name == artist):
                    found = True
                retry += 1
        else:     
            num_results = sp.search(q=parameters, type="track", limit=1)['tracks']['total']
            spotify_results = sp.search(q=parameters, type="track", limit=1, offset=random.randint(0,num_results-1))

        artist = spotify_results['tracks']['items'][0]['album']['artists'][0]['name']
        title = spotify_results['tracks']['items'][0]['name']
        popularity = spotify_results['tracks']['items'][0]['popularity']
        query = f'{title} {artist}'
        cover = spotify_results['tracks']['items'][0]['album']['images'][0]['url']
        release_date = spotify_results['tracks']['items'][0]['album']['release_date']
        album_name = spotify_results['tracks']['items'][0]['album']['name']
        spotify_url = spotify_results['tracks']['items'][0]['external_urls']['spotify']
        
        youtube_results = ytmusic.search(query, filter='songs', limit=1)
        id = youtube_results[0]['videoId']
        youtube_url = f'https://www.youtube.com/watch?v={id}'
        duration = youtube_results[0]['duration_seconds']

        try:
            deezer_results = search_deezer_track(query)
            if deezer_results:
                id = deezer_results['id']
                deezer_url = deezer_results['url']
                preview = deezer_results['preview']
                song_found = True
        except:
            pass

    return query, id, deezer_url, youtube_url, spotify_url, duration, cover, preview, genre, release_date, album_name, start_year, end_year, title, artist, popularity


def download_yt(id, query, start):
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

download_cache = {}
download_paths = {}
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
    artist = params.get('artist')
    album = params.get('album')
    track = params.get('track')
    is_test = params.get('isTest')

    if is_test:
        youtube_url = 'https://www.youtube.com/watch?v=RLBgQrvAp6Q'
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
            query, id, deezer_url, youtube_url, spotify_url, duration, cover, preview, genre, release_date, album_name, start_year, end_year, title, artist, popularity = get_random_song(genre, start_year, end_year, artist, album, track)
        except ValueError:
            return jsonify({'status': 'error', 'message': 'NO TRACKS FOUND'})
        except:
            return jsonify({'status': 'error', 'message': 'TRY AGAIN'})

    return jsonify({'status': 'success',
                    
                    'deezer_url': deezer_url,
                    'youtube_url': youtube_url,
                    'spotify_url': spotify_url,
                    'duration': duration,
                    'query': query, 
                    'title': title,
                    'artist': artist,
                    'cover': cover, 
                    'preview': preview, 
                    'genre': genre,
                    'release_date': release_date,
                    'album_name': album_name,
                    'start_year': start_year,
                    'end_year': end_year,
                    'popularity': popularity})

@app.route('/drop', methods=['POST'])
def drop():
    params = request.get_json()
    url = params.get('url')
    duration = int(params.get('duration'))
    start_time = random.randint(0,duration-5)
    is_test = params.get('isTest')

    if is_test:
        path = 'static/clips/Only One (feat. DJ Spinn & Taso).mp3'
        
    return jsonify({'path':path,'start_time':start_time})

@app.route('/pocket', methods=['POST'])
def pocket():
    params = request.get_json()
    url = params.get('url')

    tmpdir = tempfile.mkdtemp()
    if platform.system() == "Linux":
        run(['source','/root/needle-dropper/venv/bin/activate','python','dmix', url, '--path', tmpdir], check=True)
    else:
        run(['./dmix', url, '--path', tmpdir], check=True)

    files = os.listdir(tmpdir)
    if not files:
        return {'error': 'No file downloaded'}, 500

    filepath = os.path.join(tmpdir, files[0])
    file_id = str(uuid.uuid4())
    download_cache[file_id] = filepath
    return jsonify({"file_id": file_id, "filename": files[0]})

'''   
@app.route('/pocket')
def pocket():
    url = request.args.get('url')
    if not url:
        return "Missing URL", 400

    def generate():
        file_id = str(uuid.uuid4())
        tmpdir = tempfile.mkdtemp()
        cmd = f'deemix "{url}" --path {tmpdir}'
        proc = Popen(shlex.split(cmd), stdout=PIPE, stderr=PIPE, text=True)

        for line in proc.stdout:
            yield f"data: {line.strip()}\n\n"
            if "Download at 100%" in line:
                files = os.listdir(tmpdir)
                if files:
                    path = os.path.join(tmpdir, files[0])
                    download_paths[file_id] = path
                    yield f"event: done\ndata: {file_id}\n\n"

    return Response(stream_with_context(generate()), mimetype='text/event-stream')
'''
       
@app.route('/download')
def download():
    file_id = request.args.get('id')
    path = download_cache.get(file_id)
    if not path:
        return "Invalid or expired download", 404
    return send_file(path, as_attachment=True, download_name=os.path.basename(path), mimetype="audio/mpeg")

    
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