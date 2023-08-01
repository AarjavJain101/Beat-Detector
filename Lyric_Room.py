import numpy as np  # Use numpy for as many calculations as possible bc FAST!
import pyaudio  # To get audio data from mic
import tkinter as tk
import time
import spotipy
import spotipy.util as util
import syncedlyrics


# Set the parameters for the audio recording
FORMAT              = pyaudio.paInt16
CHANNELS            = 2
RECORD_SECONDS      = 9999999
RATE                = 94618  # int(43008 * 2.2)
CHUNK_SIZE          = 2048
HISTORY_SECONDS     = 1

CLAP_RANGE_LOW      = 11
HIHAT_RANGE_LOW     = 27

TOTAL_SUB_BANDS     = 39  # Each sub band is a range of 5 * frequency resolution. it is ~230Hz wide and there are 39 of these

# Set the parameters for the GUI
PROVIDER = ["MusixMatch", "NetEase"]
FONT = "Kristen ITC"

# Lover Boy type colors
# BASS_COLOR = "#0000FF"
# CLAP_COLOR = "#FF6FFF"
# HIHAT_COLOR = "#882888"

# Hype type colors
BASS_COLOR = "#FF0000"
CLAP_COLOR = "#FFFF00"
HIHAT_COLOR = "#882888"

# # Party/Club type colors
# BASS_COLOR = "#89CFEF"
# CLAP_COLOR = "#FFFF00"
# HIHAT_COLOR = "#882888"

LABEL_FG_NO_COLOR = "#FF0000"
LABEL_FG_COLOR = "#FFFFFF"

# Parameters for the timing of lyrics
EXTRA_CHUNKS = 46
TIME_LOW = -2
TIME_HIGH = 14

# Set the parameters for the Spotify API
redirect_uri = "https://www.google.com/"  # change this to your value
client_id = "CLIENT_ID"
client_secret = "CLIENT_SECRET"
username = "USERNAME"  # your Spotify username
scope = "user-read-currently-playing user-read-playback-state user-modify-playback-state"


# ===========================================================================
# Function: Gets both channel audio data and returns left channel data
# Input:    Audio data from both channels
# Return:   Left channel audio data
def getSoundAmplitudeBuffer(stream):
    data = stream.read(CHUNK_SIZE)

    # Convert data to numpy array
    audio_data = np.frombuffer(data, dtype=np.int16).reshape(-1, 2)

    # Separate audio data for left and right channels
    amplitudes_left = audio_data[:, 0]

    # Combine
    sound_amplitude_buffer = np.array(amplitudes_left)
    return sound_amplitude_buffer


# ===========================================================================
# Function: Takes the FFT of the audio data for 1 CHUNK_SIZE
# Input:    Sound Amplitude Buffer from getSoundAmplitudeBuffer
# Return:   Real amplitude values, associated frequency values
def takeFFT(audio_data, sample_rate):
    # Apply Hanning window to audio data
    window = np.hanning(len(audio_data))
    audio_data = audio_data * window
    
    # Calculate the FFT of the audio data
    amplitudes = np.fft.rfft(audio_data)
    
    # Calculate the frequency values for each point in the FFT
    freq_values = np.fft.rfftfreq(len(audio_data), d=1/sample_rate)

    # Filter the frequency data and frequency values to only show frequencies between 20Hz and 5000Hz
    mask = (freq_values >= 30) & (freq_values <= 9010)
    amplitudes = amplitudes[mask]
    
    # Return amplitudes
    return amplitudes


# ===========================================================================
# Function: Calculates the energy of each sub band
# Input:    FFT'd audio data
# Return:   List of energy for each sub band
def getSubBandInstantEnergyofChunk(audio_data_fft):
    instant_energy = []
    for i in range(TOTAL_SUB_BANDS):
        instant_energy.append(np.mean(np.power(np.abs(audio_data_fft[int(len(audio_data_fft) / TOTAL_SUB_BANDS) * i : int(len(audio_data_fft) / TOTAL_SUB_BANDS) * (i + 1)]), 3)))

    # Return the instant energy values
    return instant_energy


# ===========================================================================
# Function: Shifts the energy history list right to slot in the new instant energy at the end
# Input:    Energy history list and the instant energy
# Return:   Updated energy history list
def appendNewEnergy(energy_history, instant_energy):
    energy_history.pop(0)
    energy_history.append(instant_energy)

    return energy_history


# ===========================================================================
# Function:  Checks if a beat has occurred and prints which sub band caused the beat
# Algorithm: First normalize by dividing by max energy (from instant energy or energy history)
#            Then check if the instant energy is greater than a certain threshold based on variance 
# Input:     Instant energy and the energy history
# Return:    True if a beat occurred, otherwise False
def checkBeatSubBand(instant_energy_sub_bands, energy_history_sub_bands):
    # Declare variables for function use
    max_energy_sub_bands = []
    sub_band_thresholds = []
    avg_energies = []
    norm_avg_energies = []
    sub_band_beat = [False for i in range(TOTAL_SUB_BANDS)]
    norm_instant_energy_sub_bands = [0 for i in range(len(instant_energy_sub_bands))]
    norm_energy_history_sub_bands = [[0 for i in range(len(instant_energy_sub_bands))] for j in range(len(energy_history_sub_bands))]

    for i in range(TOTAL_SUB_BANDS):
        # Calculate the max energy for each sub band and normalize the history and Instant energy
        max_energy_sub_bands.append(np.max([history[i] for history in energy_history_sub_bands]))
        for j in range(len(energy_history_sub_bands)):
            norm_energy_history_sub_bands[j][i] = energy_history_sub_bands[j][i] / max_energy_sub_bands[i]
        norm_instant_energy_sub_bands[i] = instant_energy_sub_bands[i] / max_energy_sub_bands[i]

        # Calculate the average energy and the threshold for each sub band
        sub_band_thresholds.append(-15 * np.var([history[i] for history in norm_energy_history_sub_bands]) + 1.40)
        avg_energies.append(np.mean([history[i] for history in energy_history_sub_bands]))
        norm_avg_energies.append(np.mean([history[i] for history in norm_energy_history_sub_bands]))

        # Check if the instant energy is greater than the threshold
        if norm_instant_energy_sub_bands[i] > sub_band_thresholds[i] * norm_avg_energies[i] / 1.15 or norm_instant_energy_sub_bands[i] > 0.15:
            sub_band_beat[i] = True

    # Return the sub band beat array
    return sub_band_beat


# ===========================================================================
# Function:  Simply averages the energies from sub bands clap low to clap high which is the clap energy range 
# Input:     Instant energy for all sub bands
# Return:    Average energy in the clap low to clap high sub band region
def getClapEnergy(instant_energy):
    return (1.2 * instant_energy[CLAP_RANGE_LOW]
            + 1.3 * instant_energy[CLAP_RANGE_LOW + 1]
            + 1.5 * instant_energy[CLAP_RANGE_LOW + 2]
            + 1.4 * instant_energy[CLAP_RANGE_LOW + 5] 
            + 1.6 * instant_energy[CLAP_RANGE_LOW + 6] 
            + 1.4 * instant_energy[CLAP_RANGE_LOW + 9] 
            + 1.6 * instant_energy[CLAP_RANGE_LOW + 10]) / 10


# ===========================================================================
# Function:  Simply averages the energies from sub bands hihat low to hihat high which is the hihat energy range 
# Input:     Instant energy for all sub bands
# Return:    Average energy in the clap low to clap high sub band region
def getHiHatEnergy(instant_energy):
    return (1.3 * instant_energy[HIHAT_RANGE_LOW]
            + 1.7 * instant_energy[HIHAT_RANGE_LOW + 1]
            + 1.4 * instant_energy[HIHAT_RANGE_LOW + 2]
            + 1.2 * instant_energy[HIHAT_RANGE_LOW + 3]
            + 1.4 * instant_energy[HIHAT_RANGE_LOW + 4]) / 7


# ===========================================================================
# Function:  Confirms if the current detected beat is within an acceptable range of previous beats 
# Input:     Energy of the current detected beat and the energy history of previusly detected beats
# Return:    True if the history is less than 20 beats or the detected beat exceeds the threshold and False if not
def confirmBeat(current_detected_beat, detected_beat_history):
    max_detected_beat = np.max(detected_beat_history)
    norm_detected_beat_history = detected_beat_history / max_detected_beat
    avg_detected_beat = np.mean(detected_beat_history) / max_detected_beat
    if current_detected_beat / max_detected_beat > avg_detected_beat * np.var(norm_detected_beat_history) * 0.64:
        detected_beat_history = appendNewEnergy(detected_beat_history, current_detected_beat)
        return True
    else:
        return False


# ===========================================================================
# Function: Change window color
# Input:    The color to be changed to
# Return:   None
def changeColor(color):
    window.configure(bg=color)
    window.update()
    if color == "#000000":
        label.configure(bg=color, fg=LABEL_FG_NO_COLOR)
    else:
        label.configure(bg=color, fg=LABEL_FG_COLOR)
    label.update()


# ===========================================================================
# Function: Change the colors in a certain pattern when bass is detected
# Input:    None
# Return:   None
def bassScheme(type):
    if (type == "ultra"):
        changeColor(BASS_COLOR)
        time.sleep(0.045)
    else:
        changeColor(BASS_COLOR)
        time.sleep(0.045)


# ===========================================================================
# Function: Change the colors in a certain pattern when claps are detected
# Input:    None
# Return:   None
def clapScheme():
    changeColor(CLAP_COLOR)
    time.sleep(0.065)


# ===========================================================================
# Function: Change the colors in a certain pattern when hihats is detected
# Input:    None
# Return:   None
def hihatScheme(type):
    if (type == "ultra"):
        changeColor(HIHAT_COLOR)
        time.sleep(0.020)
    else:
        changeColor("#000000")
        time.sleep(0.001)


# ===========================================================================
# Function: Given an array of booleans return true if input num are true
# Input:    The array of Booleans and the input num required
# Return:   True if at least input num elements are true else false
def checkTrueValues(arr, input_num):
    true_count = 0

    for value in arr:
        if value:
            true_count += 1
            if true_count >= input_num:
                return True

    return False


# ===========================================================================
# Function: Flash colors based on the final detection
# Input:    The final detection array
# Return:   None
def flashColors(final_detection, type):
    if (final_detection[0] and not final_detection[1] and final_detection[2]):
        bassScheme(type)
    elif (final_detection[0] and not final_detection[1] and not final_detection[2]):
        bassScheme(type)
    elif (not final_detection[0] and final_detection[1] and final_detection[2]):
        clapScheme()
    elif (final_detection[0] and final_detection[1] and final_detection[2]):
        clapScheme()
    elif (not final_detection[0] and final_detection[1] and not final_detection[2]):
        clapScheme()
    elif (not final_detection[0] and not final_detection[1] and final_detection[2]):
        hihatScheme(type)


# ===========================================================================
# Function: Get the token for spotify
# Input:    None
# Return:   The token if not then none
def get_spotify_client():
    token = util.prompt_for_user_token(username, scope, client_id=client_id,
                                       client_secret=client_secret, redirect_uri=redirect_uri)
    if token:
        return spotipy.Spotify(auth=token)
    else:
        print("Can't get token for", username)
        return None


# ===========================================================================
# Function: Get the current song playing
# Input:    The spotify client
# Return:   The song name and artist name
def get_currently_playing_song(sp):
    currently_playing = sp.current_playback()

    if currently_playing and currently_playing.get('is_playing'):
        song_name = currently_playing['item']['name']
        artists = currently_playing['item']['artists']
        artist_names = ', '.join([artist['name'] for artist in artists])
        return song_name, artist_names
    else:
        print("No song currently playing.")
        return None, None


# ===========================================================================
# Function: Given a string, remove the () brakcets and its contents
# Input:    The string with the brackets
# Return:   The string without the brackets
def removeBrackets(input_string):
    if input_string == "":
        return input_string
    
    result = []
    open_brackets_count = 0
    brackets_count = 0
    brackets_index = []

    if input_string[0] == '(' and input_string[-1] == ')':
        return input_string[1:-1]
    
    for index, char in enumerate(input_string):
        if char == '(' or char == ')':
            brackets_index.append(index)
            brackets_count += 1
    
    if brackets_count == 0:
        return input_string
    elif brackets_count == 1:
        for char in input_string:
            if char != '(' and char != ')':
                result.append(char)
    else:
        for char in input_string:
            if char == '(':
                open_brackets_count += 1
            elif char == ')':
                open_brackets_count = max(0, open_brackets_count - 1)
            elif open_brackets_count == 0:
                result.append(char)

    return ''.join(result)


# ===========================================================================
# Function: Parse the lyrics of the song
# Input:    The big string with the time stamps and the lyrics
# Return:   The time stamps in chunks and the lines by lines lyrics
def parseLyrics(lrc):
    # Initiliaze time=stamp list, lyric list, and chunk time constant
    time_stamps = []
    all_lines = []

    chunk_in_ms = (CHUNK_SIZE / RATE) * 1000

    i = 0
    while (i < len(lrc)): 
        if (lrc[i] == '['):
            # Calculate time stamp as chunks
            minutes = int(lrc[i + 1 : i + 3])
            seconds = float(lrc[i + 4 : i + 9])

            time_stamps.append(round((minutes * 60 * 1000 + seconds * 1000) / chunk_in_ms))
            i = lrc.index(']', i)
            if lrc[i] == " ":
                i += 2
            else:
                i += 1
        else:
            line_start = i
            while (i < len(lrc) and lrc[i] != '['):
                i += 1
            line = lrc[line_start : i - 1]
            line = removeBrackets(line)
            all_lines.append(line)

    return time_stamps, all_lines


# ===========================================================================
# Function: Given a line, calculate the time for each word
# Input:    The line and the chunks for the line
# Return:   The line with the time for each word
def timeWords(line, chunks_for_line):
    words = line.split(" ")
    char_sum = 0
    timed_line = []
    total_chunks = 0
    total_words = ""
    for i in range(len(words)):
        char_sum += len(words[i])
    if char_sum == 0:
        timed_line.append([" ", chunks_for_line])
    else:
        for i in range(len(words)):
            total_chunks += int((len(words[i]) / char_sum) * chunks_for_line)
            if i == len(words) - 1:
                total_words += words[i]
            else:
                total_words += words[i] + " "
            timed_line.append([total_words, total_chunks])
    return timed_line


# ===========================================================================
# Function: Start the recording, calculations, and lights of the program
# Input:    None
# Return:   None
def click():
    time_start = time.perf_counter()
    # Create an instance of the PyAudio class and Open a stream to record audio from your microphone
    audio = pyaudio.PyAudio()
    stream = audio.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK_SIZE)
    print("Recording started...")

    # Initialize a counter for the number of chunks processed, list to store audio_data, instant energy values, and history of energies for ~ 1s of data
    chunks_processed = 0
    lyrics_chunks = 0
    time_stamp_index = 0
    sound_amplitude_buffer = np.array([0 for samples in range(CHUNK_SIZE)], dtype=object)
    instant_energy_sub_bands = []
    energy_history_sub_bands = []
    sub_band_beat = []
    beat_history = []  # Currently only tracks bass and clap
    for i in range(3):
        beat_history.append([])

    bass_chunk = 0
    clap_energy = 0
    clap_chunk = 0
    hihat_energy = 0
    hihat_chunk = 0
    hihat_gap_array = []
    hihat_gap_average = 0
    hihat_gap_mode = 0

    lines = []
    times = []
    isNewSong = False
    skipText = False
    word_count = 0

    final_detection = [False, False, False]

    sp = get_spotify_client()
    if sp:
        last_song_name = None
        last_artist_names = None

        # Record audio for HISTORY_SECONDS to fill energy history
        while chunks_processed < (HISTORY_SECONDS * int(RATE / CHUNK_SIZE)):
            # Do processing
            sound_amplitude_buffer = getSoundAmplitudeBuffer(stream)
            real_amp_data = takeFFT(sound_amplitude_buffer, RATE)
            instant_energy_sub_bands = getSubBandInstantEnergyofChunk(real_amp_data)
            energy_history_sub_bands.append(instant_energy_sub_bands)
            chunks_processed += 1

        # Continue recording audio until the RECORD_SECONDS is fulfilled
        while chunks_processed < ((RECORD_SECONDS)* int(RATE / CHUNK_SIZE)):            
            # Get audio data
            sound_amplitude_buffer = getSoundAmplitudeBuffer(stream)

            # Get the lyrics
            if (chunks_processed - 46) % int(1 * (RATE / CHUNK_SIZE)) == 0:
                song_name, artist_names = get_currently_playing_song(sp)
                if song_name and artist_names:
                    if song_name != last_song_name or artist_names != last_artist_names:
                        print(f"Currently playing: {song_name} by {artist_names}")
                        if chunks_processed != 46:
                            time_start = time.perf_counter()

                        lrc = syncedlyrics.search(f"[{song_name}] [{artist_names}]", providers=[PROVIDER[0]])
                        if not lrc:
                            lrc = syncedlyrics.search(f"[{song_name}] [{artist_names}]", providers=[PROVIDER[1]])
                            if lrc:
                                print(lrc)
                                times, lines = parseLyrics(lrc)
                                if len(times) > len(lines):
                                    lines.append(" ")
                                times.append(times[-1] + 50)
                                time_stamp_index = 0
                                word_count = 0
                                isNewSong = True
                            else:
                                print("No lyrics found")
                                label.config(text="", font=(FONT, 60, "bold", "italic"))
                                skipText = True
                        else:
                            print(lrc)
                            times, lines = parseLyrics(lrc)
                            if len(times) > len(lines):
                                lines.append(" ")
                            times.append(times[-1] + 50)
                            time_stamp_index = 0
                            word_count = 0
                            isNewSong = True

                        last_song_name = song_name
                        last_artist_names = artist_names
            
            # Do Processing
            final_detection = [False, False, False]
            real_amp_data = takeFFT(sound_amplitude_buffer, RATE)
            instant_energy_sub_bands = getSubBandInstantEnergyofChunk(real_amp_data)
            sub_band_beat = checkBeatSubBand(instant_energy_sub_bands, energy_history_sub_bands)

            # Checks Bass
            if (sub_band_beat[0]):
                if chunks_processed - bass_chunk > 8:
                    if len(beat_history[0]) >= 4:
                        if (confirmBeat(instant_energy_sub_bands[0], beat_history[0])):
                            # print(f"Bass {chunks_processed} Energy {instant_energy_sub_bands[0]:.2e}")
                            final_detection[0] = True
                            bass_chunk = chunks_processed
                    else:
                        beat_history[0].append(instant_energy_sub_bands[0])
        

            # Checks Clap
            clap_energy = getClapEnergy(instant_energy_sub_bands)
            if (sub_band_beat[CLAP_RANGE_LOW] and sub_band_beat[CLAP_RANGE_LOW + 1] and sub_band_beat[CLAP_RANGE_LOW + 2] and sub_band_beat[CLAP_RANGE_LOW + 5] and sub_band_beat[CLAP_RANGE_LOW + 6] and sub_band_beat[CLAP_RANGE_LOW + 9] and sub_band_beat[CLAP_RANGE_LOW + 10]):
                if chunks_processed - clap_chunk >= 4:
                    if len(beat_history[1]) >= 3:
                        if (confirmBeat(clap_energy * 1.6, beat_history[1])):
                            # print(f"Gap: {chunks_processed - clap_chunk} Clap {chunks_processed} Energy {clap_energy:.2e}")
                            final_detection[1] = True 
                            clap_chunk = chunks_processed
                    else:
                        beat_history[1].append(clap_energy)
            
            # Check HiHat
            hihat_energy = getHiHatEnergy(instant_energy_sub_bands)
            if (checkTrueValues([sub_band_beat[HIHAT_RANGE_LOW], sub_band_beat[HIHAT_RANGE_LOW + 1], sub_band_beat[HIHAT_RANGE_LOW + 2], sub_band_beat[HIHAT_RANGE_LOW + 3], sub_band_beat[HIHAT_RANGE_LOW + 4]], 1)):
                if chunks_processed - hihat_chunk > 3:
                    if len(beat_history[2]) >= 5:
                        if (confirmBeat(hihat_energy, beat_history[2])):
                            # print(f"Gap:{chunks_processed - hihat_chunk} HiHat {chunks_processed} Energy {hihat_energy:.2e}")
                            if (len(hihat_gap_array) < 35):
                                hihat_gap_array.append(chunks_processed - hihat_chunk)
                            else:
                                hihat_gap_average = np.average(hihat_gap_array)
                                hihat_gap_mode = np.bincount(hihat_gap_array).argmax()
                                hihat_gap_array = []
                            final_detection[2] = True
                            hihat_chunk = chunks_processed
                    else:
                        beat_history[2].append(hihat_energy)
            
            if (hihat_gap_mode > 0 and np.abs((hihat_gap_average / hihat_gap_mode) - 1) < 0.50 and hihat_gap_mode >= 7):
                flashColors(final_detection, "ultra") 
            else: 
                flashColors(final_detection, "normal")
            changeColor("#000000")

            if not skipText:
                # Set lyrics chunks and remove passed lyrics
                lyrics_chunks = int((time.perf_counter() - time_start) / (CHUNK_SIZE / RATE))
                if isNewSong:
                    line_index = 0
                    while line_index < len(times) and lyrics_chunks >= times[line_index] + TIME_HIGH:
                        line_index += 1
                    while line_index > 0:
                        times.pop(0)
                        lines.pop(0)
                        line_index -= 1
                    isNewSong = False


                # Is the lyric chunk timed for the current line?
                lyrics_chunks = int((time.perf_counter() - time_start) / (CHUNK_SIZE / RATE))
                timed_line = timeWords(lines[time_stamp_index], times[time_stamp_index + 1] - times[time_stamp_index])
                if lyrics_chunks >= times[time_stamp_index]:

                    # Is the lyric chunk timed for the next word in the line?
                    if lyrics_chunks < times[time_stamp_index] + timed_line[word_count][1]:

                        # Change label Font based on length of line
                        if len(timed_line[word_count][0]) < 13:
                            label.config(text=timed_line[word_count][0], font=(FONT, 80, "bold", "italic"))
                        elif len(timed_line[word_count][0]) < 22:
                            label.config(text=timed_line[word_count][0], font=(FONT, 75, "bold", "italic"))
                        elif len(timed_line[word_count][0]) < 28:
                            label.config(text=timed_line[word_count][0], font=(FONT, 65, "bold", "italic"))
                        elif len(timed_line[word_count][0]) < 100:
                            label.config(text=timed_line[word_count][0], font=(FONT, 60, "bold", "italic"))
                    else:
                        word_count += 1

                if word_count == len(timed_line):
                    word_count = 0
                    if time_stamp_index < len(times) - 2:
                        time_stamp_index += 1

                label.update()
        
            energy_history_sub_bands = appendNewEnergy(energy_history_sub_bands, instant_energy_sub_bands)
            chunks_processed += 1


    print("Recording stopped.")

    # Close the audio stream
    stream.stop_stream()
    stream.close()
    audio.terminate()


# Create the window
window = tk.Tk()
window.title("Light Room")
window.geometry("500x500")
window.configure(bg="black")

label = tk.Label(window, text="", font=("Kristen ITC", 25), bg="black", fg="yellow", wraplength=1200, justify="center")
label.pack(fill=tk.BOTH, expand=True)

window.update_idletasks()
window_width = window.winfo_reqwidth()
window_height = window.winfo_reqheight()
screen_width = window.winfo_screenwidth()
screen_height = window.winfo_screenheight()
x = int((screen_width - window_width) / 2)
y = int((screen_height - window_height) / 2)
window.geometry(f"{window_width}x{window_height}+{x}+{y}")


# Create button to start stream
start_button = tk.Button(window, text="Start", command=click)
start_button.pack()

# Run the window
window.mainloop()