import spotipy
import spotipy.util as util

# Change these to your values
redirect_uri = "https://www.google.com/" 
client_id = "client_id"
client_secret = "client_secret"
username = "username"

# Need this scope
scope = "playlist-read-private playlist-read-collaborative user-library-read"

# Get Token (copy paste google link)
token = util.prompt_for_user_token(username, scope, client_id=client_id, client_secret=client_secret, redirect_uri=redirect_uri)

if token:
    sp = spotipy.Spotify(auth=token)
    playlists = sp.current_user_playlists(limit=50)

    # Loop through all tracks and put in songs.txt
    with open("songs.txt", "w", encoding="utf-8") as file:
        for playlist in playlists["items"]:
            playlist_name = playlist['name']
            results = sp.playlist_tracks(playlist["id"], fields="items(track(name,artists(name)))")
            for idx, item in enumerate(results["items"]):
                track_name = item["track"]["name"]
                artist_names = ", ".join([artist["name"] for artist in item["track"]["artists"]])
                song_line = f"{artist_names} - {track_name}\n"
                file.write(song_line)

else:
    print("Could not get token for:", username)
