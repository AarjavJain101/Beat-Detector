import numpy as np  # Use numpy for as many calculations as possible bc FAST!
import pyaudio  # To get audio data from mic


# Set the parameters for the audio recording
FORMAT              = pyaudio.paInt16
CHANNELS            = 2
RECORD_SECONDS      = 500000
RATE                = 94618  # int(43008 * 2.2)
CHUNK_SIZE          = 2048
HISTORY_SECONDS     = 1

CLAP_RANGE_LOW      = 11
HIHAT_RANGE_LOW     = 27

TOTAL_SUB_BANDS     = 39  # Each sub band is a range of 5 * frequency resolution. it is ~230Hz wide and there are 39 of these


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
def checkBeatInChunk(instant_energy_sub_bands, energy_history_sub_bands):
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
def compareBeat(current_detected_beat, detected_beat_history):
    max_detected_beat = np.max(detected_beat_history)
    norm_detected_beat_history = detected_beat_history / max_detected_beat
    avg_detected_beat = np.mean(detected_beat_history) / max_detected_beat
    if current_detected_beat / max_detected_beat > avg_detected_beat * np.var(norm_detected_beat_history) * 0.64:
        detected_beat_history = appendNewEnergy(detected_beat_history, current_detected_beat)
        return True
    else:
        return False


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
beat_history = []  # Currently only tracks bass and clap
for i in range(3):
    beat_history.append([])

bass_chunk = 0
clap_energy = 0
clap_chunk = 0
hihat_energy = 0
hihat_chunk = 0

final_detection = [False, False, False]

time_sum = 0

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
    final_detection = [False, False, False]
    
    # Do processing
    sound_amplitude_buffer = getSoundAmplitudeBuffer(stream)
    real_amp_data = takeFFT(sound_amplitude_buffer, RATE)
    instant_energy_sub_bands = getSubBandInstantEnergyofChunk(real_amp_data)
    sub_band_beat = checkBeatInChunk(instant_energy_sub_bands, energy_history_sub_bands)


    # Checks Bass
    if (sub_band_beat[0]):
        if chunks_processed - bass_chunk > 8:
            if len(beat_history[0]) >= 4:
                if (compareBeat(instant_energy_sub_bands[0], beat_history[0])):
                    # print(f"Bass {chunks_processed} Energy {instant_energy_sub_bands[0]:.2e}")
                    final_detection[0] = True
                    bass_chunk = chunks_processed
            else:
                beat_history[0].append(instant_energy_sub_bands[0])


    # Checks Clap
    clap_energy = getClapEnergy(instant_energy_sub_bands)
    if (checkTrueValues([sub_band_beat[CLAP_RANGE_LOW], sub_band_beat[CLAP_RANGE_LOW + 1], sub_band_beat[CLAP_RANGE_LOW + 2], sub_band_beat[CLAP_RANGE_LOW + 5], sub_band_beat[CLAP_RANGE_LOW + 6], sub_band_beat[CLAP_RANGE_LOW + 9], sub_band_beat[CLAP_RANGE_LOW + 10]], 7)):
        if chunks_processed - clap_chunk >= 4:
            if len(beat_history[1]) >= 3:
                if (compareBeat(clap_energy * 1.6, beat_history[1])):
                    print(f"Gap: {chunks_processed - clap_chunk} Clap {chunks_processed} Energy {clap_energy:.2e}")
                    final_detection[1] = True 
                    clap_chunk = chunks_processed
            else:
                beat_history[1].append(clap_energy)
    

    # Check HiHat
    hihat_energy = getHiHatEnergy(instant_energy_sub_bands)
    if (checkTrueValues([sub_band_beat[HIHAT_RANGE_LOW], sub_band_beat[HIHAT_RANGE_LOW + 1], sub_band_beat[HIHAT_RANGE_LOW + 2], sub_band_beat[HIHAT_RANGE_LOW + 3], sub_band_beat[HIHAT_RANGE_LOW + 4]], 1)):
        if chunks_processed - hihat_chunk > 3:
            if len(beat_history[2]) >= 5:
                if (compareBeat(hihat_energy, beat_history[2])):
                    # print(f"Gap:{chunks_processed - hihat_chunk} HiHat {chunks_processed} Energy {hihat_energy:.2e}")
                    final_detection[2] = True
                    hihat_chunk = chunks_processed
            else:
                beat_history[2].append(hihat_energy)


    energy_history_sub_bands = appendNewEnergy(energy_history_sub_bands, instant_energy_sub_bands)
    chunks_processed += 1


print("Recording stopped.")

# Close the audio stream
stream.stop_stream()
stream.close()
audio.terminate()