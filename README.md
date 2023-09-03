# Beat-Detector
* This is a C\C++ and Python program that detects bass, claps, and hi-hats in music. Works well with hip-hop, rap, and party music.
* Download and Run the **Beat_Tracking.exe** to use the application. **Windows Only**

## Usage
* **"Beat_Detector_No_Video.py"** - Opens mic and prints what type of beat was detected in the terminal.
* **"Beat_Detector_With_Video.py"** - Opens mic, prints the type of beat that was detected, creates frames and fills **Frames_FFT** folder, then creates and adds the no audio video, with audio video, and .wav file  to the **Videos** folder. These videos are the FFT ENERGY spectrum (blue) as the song is played WITH the orange-colored thresholds for beats in a certain frequency band.
* **"Beat_Tracking.cpp"** - Compile and download with `./build.sh` command. **CREDIT TO [Rhys Byers](https://github.com/rhys-b)** for helping develop the GUI for the light room experience.
* **"Beat_Tracking.exe"** - Pre-complied and standalone executable. Run it for the GUI light room experience.
* **"Light_Room.py"** - Opens mic, creates GUI, click start to run the beat detection and flash lights on screen to the beat.
* **"Lyric_Room.py"** - Opens mic, creates GUI, you play a song from Spotify, then click start to run the beat detection and synched lyrics. Note that the program will try to find the lyrics. If not the program simply does not display them. Also, you need to register your app on Spotify then go to the dashboard and get the client_id, client_secret, and find your username.
* **"Frostbite (Remix) - Offset.mp4"** - Video example of the **"Lyric_Room.py"** using the song "Frostbite" by Offset. This displays silver hihats, blue bass, and orange claps with synched lyrics.
* **build.sh** - The shell script for compiling **"Beat_Tracking.cpp"** with the necessary dependencies. See **Dependencies** below.
* **"filterSongs.py"** - Used to find which songs have searchable lyrics assuming a format like "ARTIST_NAMES - SONG_NAME".
* **"getUserTracks.py"** - Used to fetch all the songs in one's Spotify library. Make sure to set up the app in Spotify to get the client_id, client_secret, and find your username.
*  **Adjust Parameters and Colors as Desired**

## Dependencies (For each File)
* **"Beat_Detector_No_Video.py"** - pyaudio, numpy.
* **"Beat_Detector_With_Video.py"** - pyaudio, numpy, matplotlib.pyplot, OpenCV, wave.
* **"Beat_Tracking.cpp"** - portaudio.h, fftw3.h. These will automatically downloaded and complied with the command `./build.sh'.
* **"Light_Room.py"** - pyaudio, numpy, tkinter
* **"Lyric_Room.py"** - pyaudio, numpy, tkinter, [spotipy](https://github.com/spotipy-dev/spotipy), [synchedlyrics](https://github.com/rtcq/syncedlyrics).
* **"filterSongs.py"** - [synchedlyrics](https://github.com/rtcq/syncedlyrics).
* **"getUserTracks.py"** - [spotipy](https://github.com/spotipy-dev/spotipy)

## Parameters
* RATE              = 94618
* CHUNK_SIZE        = 2048
* HISTORY_SECONDS   = 1

* CLAP_RANGE_LOW      = 11
* HIHAT_RANGE_LOW     = 27

* TOTAL_SUB_BANDS     = 39  # Each sub band is a range of 5 * frequency resolution. it is ~230Hz wide and there are 39 of these

### Set the parameters for the GUI
* PROVIDER = ["MusixMatch", "NetEase"]
* FONT = "Kristen ITC"

### Calm Pink Type Colors
BASS_COLOR = "#0000FF"
CLAP_COLOR = "#FF6FFF"
HIHAT_COLOR = "#882888"

### Hype type colors
* BASS_COLOR = "#FF0000"
* CLAP_COLOR = "#FFFF00"
* HIHAT_COLOR = "#882888"

### Party/Club type colors
* BASS_COLOR = "#89CFEF"
* CLAP_COLOR = "#FFFF00"
* HIHAT_COLOR = "#882888"

* LABEL_FG_NO_COLOR = "#FF0000"
* LABEL_FG_COLOR = "#FFFFFF"

## Note
Please make sure that all the folders are present together with the video Python file to run.
