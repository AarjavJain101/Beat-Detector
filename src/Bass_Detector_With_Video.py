import numpy as np  # Use numpy for as many calculations as possible bc FAST!
import pyaudio  # To get audio data from mic
import time  # For testing how long the processing takes
import matplotlib.pyplot as plt  # For visualization of FFT
import os  # Doing ffmpeg commands and making folders
import cv2 as cv  # Making a movie out of a bunch of frames
import shutil  # Deleting folders with stuff in them
import wave  # Convert audio data to .wav format


# Set the parameters for the audio recording
FORMAT              = pyaudio.paInt16
CHANNELS            = 2
RECORD_SECONDS      = 199
RATE                = 94618  # int(43008 * 2.2)
CHUNK_SIZE          = 2048
HISTORY_SECONDS     = 1

TOTAL_SUB_BANDS     = 39  # Each sub band is a range of 5 * frequency resolution. it is ~185Hz wide and there are 39 of these


# ===========================================================================
# Function: Gets both left and right channel audio but just returns left for now
# Input:    Audio data from both channels
# Return:   Left channel audio data
def getSoundAmplitudeBuffer(stream):
    data = stream.read(CHUNK_SIZE)

    # Convert data to numpy array (CHUNK_SIZE, CHANNELS)
    audio_data = np.frombuffer(data, dtype=np.int16).reshape(-1, 2)

    # Separate audio data for left and right channels
    amplitudes_left = audio_data[:, 0]
    amplitudes_right = audio_data[:, 1]

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
    freq_values = freq_values[mask]
    amplitudes = amplitudes[mask]
    
    
    # Return the real part of the FFT, the associated frequency values,
    return np.real(freq_values), amplitudes


# ===========================================================================
# Function: Perfrom absolute value, square all values, then normalize all values to a maximum magnitiude of 10
# Input:    FFT'd audio data
# Return:   enevlope followed FFT'd audio data
def envelopeFollowFFT(audio_data_fft):
    # Calculate the magnitude of the FFT'd audio data
    mag = np.power(np.abs(audio_data_fft), 3)
    
    # Normalize the magnitude to a range of 0 to 10
    # mag = mag / np.max(mag) * 10
    
    # Return the normalized FFT'd audio data
    return mag


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
# Function: Determine the time taken for a single chunk to be read and processed
# Input:    Start time, end time, number of chunks processed
# Return:   Time taken
def getTimeTaken(start_time, end_time, chunks_processed):
    time_taken = end_time - start_time
    # print(f"Time taken for frame {chunks_processed}: {time_taken:.2f} ms")

    return time_taken


# ===========================================================================
# Function:  Checks if a beat has occurred and prints which sub band caused the beat
# Algorithm: First normalize by dividing by max energy (from instant energy or energy history)
#            Then check if the instant energy is greater than a certain threshold based on variance 
# Input:     Instant energy and the energy history
# Return:    True if a beat occurred, otherwise False
def checkBeatSubBand(instant_energy_sub_bands, energy_history_sub_bands):
    # Normalize the energy history and instant energy using the maximum energy for each sub band
    max_energy_sub_bands = []
    sub_band_thresholds = []
    avg_energies = []
    norm_avg_energies = []
    conditions_f = []
    sub_band_beat = [False for i in range(TOTAL_SUB_BANDS)]
    norm_instant_energy_sub_bands = [0 for i in range(len(instant_energy_sub_bands))]
    norm_energy_history_sub_bands = [[0 for i in range(len(instant_energy_sub_bands))] for j in range(len(energy_history_sub_bands))]
    for i in range(TOTAL_SUB_BANDS):
        max_energy_sub_bands.append(np.max([history[i] for history in energy_history_sub_bands]))
        for j in range(len(energy_history_sub_bands)):
            norm_energy_history_sub_bands[j][i] = energy_history_sub_bands[j][i] / max_energy_sub_bands[i]
        norm_instant_energy_sub_bands[i] = instant_energy_sub_bands[i] / max_energy_sub_bands[i]
        sub_band_thresholds.append(-15 * np.var([history[i] for history in norm_energy_history_sub_bands]) + 1.40)
        avg_energies.append(np.mean([history[i] for history in energy_history_sub_bands]))
        norm_avg_energies.append(np.mean([history[i] for history in norm_energy_history_sub_bands]))
        conditions_f.append(sub_band_thresholds[i] * avg_energies[i] / 1.15)

        if norm_instant_energy_sub_bands[i] > sub_band_thresholds[i] * norm_avg_energies[i] / 1.15 or norm_instant_energy_sub_bands[i] > 0.15 * max_energy_sub_bands[i]:
            sub_band_beat[i] = True
    return conditions_f, sub_band_beat


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
# Function: Simple function to make a folder with specified name
# Input:    Name of folder to make
# Return:   None
def makeFolder(folder_name):
    try:
        shutil.rmtree(folder_name)
    except Exception as e:
        print(f"Failed to delete {folder_name}. Reason: {e}")

    # Create the directory again
    os.mkdir(folder_name)


# ===========================================================================
# Function: Make plots of fft data which serve as frames for the video. Saves to a folder called "Frames_FFT" and frames are ordered by number
# Input:    Total chunks processed, all frequency values, all amplitude values, type of plot (FFT or raw audio data)
# Return:   None
def makePlotsWithThreshold(chunks_processed, all_x_values, all_y_values, all_conditions, type):
    if type == 'FFT':
        makeFolder("Frames_FFT")

        all_conditions_as_y = [[0 for i in range(int(len(all_x_values[0]) / TOTAL_SUB_BANDS) * len(all_conditions[0]))] for j in range(len(all_conditions))]
        for i in range(len(all_conditions)):
            for j in range(len(all_conditions[0])):
                for k in range(int(len(all_x_values[0]) / TOTAL_SUB_BANDS)):
                    all_conditions_as_y[i][int(len(all_x_values[0]) / TOTAL_SUB_BANDS) * j + k] = all_conditions[i][j]

        for i in range(chunks_processed):
            # Plot the frequency data
            plt.plot(all_x_values[i], all_y_values[i])
            plt.plot(all_x_values[i], all_conditions_as_y[i], color='orange')
            plt.xlabel(f"Frequency (Hz) {i}")
            plt.ylabel(f"Amplitude {i}")
            plt.ylim([0, 5e19])
            plt.xlim([0, 500])
            plt.savefig(f"Frames_FFT/frame_{(i+1):04d}.png")
            plt.close()
    elif type == 'Audio':
        makeFolder("Frames_Audio")

        for i in range(chunks_processed):
            # Plot the Raw Audio Data
            plt.plot(all_x_values[i], all_y_values[i])
            plt.xlabel(f"Time (s) {i}")
            plt.ylabel(f"Amplitude {i}")
            plt.ylim([-9000, 9000])
            plt.savefig(f"Frames_Audio/frame_{(i+1):04d}.png")
            plt.close()


# ===========================================================================
# Function: Make a movie out of the frames in the specified folder
# Input:    FPS of the movie, path to the folder with the frames, name of the output movie, audio data
# Return:   None
def makeMovie(fps, path, output_name, audio_data):
    frame_files = os.listdir(path)  # Get the list of frame files in the specified path
    frame_path = os.path.join(path, frame_files[0])  # Get the path of the first frame

    # Read the first frame to get its size and properties
    frame = cv.imread(frame_path)
    height, width, channels = frame.shape

    # Define the video writer with the given output name, codec, FPS, and size
    fourcc = cv.VideoWriter_fourcc(*'mp4v')
    output_path = os.path.join("Videos", output_name)
    video_writer = cv.VideoWriter(output_path, fourcc, fps, (width, height))

    # Iterate through each frame file and add it to the video
    for file_name in frame_files:
        frame_path = os.path.join(path, file_name)
        frame = cv.imread(frame_path)
        video_writer.write(frame)

    video_writer.release()  # Release the video writer

    # Save the audio to a WAV file
    p = pyaudio.PyAudio()
    audio_file = "audio.wav"
    audio_path = os.path.join("Videos", audio_file)

    wf = wave.open(audio_path, "wb")
    wf.setnchannels(1)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b"".join(audio_data))
    wf.close()
    
    os.system(f"ffmpeg -i Videos/{output_name} -i Videos/{audio_file} -c:v copy -c:a aac -map 0:v -map 1:a Videos/{output_name}_with_audio.mp4")


# ===========================================================================
# Start program

# Create an instance of the PyAudio class and Open a stream to record audio from your microphone
audio = pyaudio.PyAudio()
stream = audio.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK_SIZE)
print("Recording started...")

# Initialize a counter for the number of chunks processed, list to store audio_data, instant energy values, and history of energies for ~ 1s of data
chunks_processed = 0
sound_amplitude_buffer = np.array([0 for samples in range(CHUNK_SIZE)], dtype=object)
instant_energy_sub_bands = []
energy_history_sub_bands = []
sub_band_beat = []
beat_history = []
for i in range(TOTAL_SUB_BANDS):
    beat_history.append([])
bass_chunk = 0

# Initialize lists to store all the data for plotting purposes
all_freq_values = []
all_real_amp_data = []
all_conditions = []
all_sound = []
conditions = []


time_sum = 0

# Record audio for HISTORY_SECONDS to fill energy history
while chunks_processed < (HISTORY_SECONDS * int(RATE / CHUNK_SIZE)):
    start_time = time.time() * 1000 # Record the start time in milliseconds

    # Do processing
    sound_amplitude_buffer = getSoundAmplitudeBuffer(stream)
    freq_values, real_amp_data = takeFFT(sound_amplitude_buffer, RATE)
    instant_energy_sub_bands = getSubBandInstantEnergyofChunk(real_amp_data)
    energy_history_sub_bands.append(instant_energy_sub_bands)
    chunks_processed += 1

    end_time = time.time() * 1000 # Record the end time in milliseconds
    time_sum += getTimeTaken(start_time, end_time, chunks_processed)

# Continue recording audio until the RECORD_SECONDS is fulfilled
while chunks_processed < ((RECORD_SECONDS)* int(RATE / CHUNK_SIZE)):
    start_time = time.time() * 1000 # Record the start time in milliseconds

    # Do processing
    sound_amplitude_buffer = getSoundAmplitudeBuffer(stream)
    all_sound.append(sound_amplitude_buffer)
    freq_values, real_amp_data = takeFFT(sound_amplitude_buffer, RATE)
    instant_energy_sub_bands = getSubBandInstantEnergyofChunk(real_amp_data)
    conditions, sub_band_beat = checkBeatSubBand(instant_energy_sub_bands, energy_history_sub_bands)
    all_conditions.append(conditions)
    if (sub_band_beat[0]):
        if chunks_processed - bass_chunk > 4:
            if len(beat_history[0]) >= 10:
                if (confirmBeat(instant_energy_sub_bands[0], beat_history[0])):
                    print(f"Bass {chunks_processed} Energy {instant_energy_sub_bands[0]:.2e}")
                    bass_chunk = chunks_processed
            else:
                beat_history[0].append(instant_energy_sub_bands[0])

    energy_history_sub_bands = appendNewEnergy(energy_history_sub_bands, instant_energy_sub_bands)
    real_amp_data = envelopeFollowFFT(real_amp_data)
    all_freq_values.append(freq_values)
    all_real_amp_data.append(real_amp_data)

    chunks_processed += 1

    end_time = time.time() * 1000 # Record the end time in milliseconds
    time_sum += getTimeTaken(start_time, end_time, chunks_processed)


print(f"Averge time for {round(CHUNK_SIZE / RATE * 1000, 2)} ms process: {time_sum/(chunks_processed):.2f} ms")
print("Recording stopped.")

makePlotsWithThreshold(chunks_processed - (HISTORY_SECONDS * int(RATE / CHUNK_SIZE)), all_freq_values, all_real_amp_data, all_conditions, 'FFT')
makeFolder("Videos")
makeMovie(RATE / CHUNK_SIZE, 'Frames_FFT', 'FFT_video.mp4', all_sound)

# Close the audio stream
stream.stop_stream()
stream.close()
audio.terminate()
