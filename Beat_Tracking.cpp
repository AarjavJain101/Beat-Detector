/* ===========================================================================      *
 * Author   :   Aarjav Jain                                                         *
 * Date     :   2023-06-04                                                          *
 * Purpose  :   Determine when bass and claps occur in real-time (mainly rap)       */


/* ========================== DEPENDENCIES ========================== */
#include <vector>
#include <cstring>
#include <portaudio.h>
#include <complex.h>
#include <fftw3.h>
#include <math.h>
#include <iostream>


/* ========================== PARAMETERS ========================== */

#define CHANNELS            1
#define RECORD_SECONDS      50
#define RATE                94618 
#define CHUNK_SIZE          2048
#define HISTORY_SECONDS     1
#define FORMAT              paFloat32

#define CLAP_RANGE_LOW      11
#define HIHAT_RANGE_LOW     27

#define TOTAL_SUB_BANDS     39  // Each sub band is a range of 5 * frequency resolution. it is ~185Hz wide and there are 39 of these

#define REAL                0
#define IMAG                1

using namespace std;


/* ========================== FUNCTION DEFINITIONS ========================== */

/* ===========================================================================      *
 * Function :   Checks and prints the Port Audio error                              *
 * Input    :   The Port Audio error                                                *
 * Return   :   NONE                                                                */
static void checkErr(PaError err)
{
    if (err != paNoError)
    {
        printf("PortAudio error: %s\n", Pa_GetErrorText(err));
        exit(1);
    }
}


/* ===========================================================================      *
 * Function :   Finds the maximum of two values                                     *
 * Input    :   Two floating point numbers                                          *
 * Return   :   The larger of the two numbers                                       */
static inline float max(float a, float b)
{
    return a > b ? a : b;   // If a > b, return a, else return b
}


/* ===========================================================================      *
 * Function :   Calculates the energy of each sub band                              *
 * Input    :   FFT'd audio data                                                    *
 * Return   :   NONE (pass by reference)                                            */
void getInstantEnergy(fftw_complex* amplitude_data, vector<float>& instant_energy)
{
    // Calculate the energy of each sub band
    for (int i = 0; i < TOTAL_SUB_BANDS; i++)
    {
        float energy = 0;
        for (int j = i * 5; j < (i + 1) * 5; j++)
        {
            energy += pow(abs(amplitude_data[j + 1][REAL]), 3.0);
        }
        energy = energy / 5.0;
        instant_energy[i] = energy;
    }
}


/* ===========================================================================      *
 * Function :  Checks if a beat occurred for each sub band                          *
 *     Algorithm:   1.  First normalize by dividing by max energy                   *
 *                  2.  Then check if instant energy > threshold based on variance  *
 *                  3.  Fill a vector of true and false values for each sub band    *
 * Input    :  Instant energy and the energy history                                *
 * Return   :  NONE (pass by reference)                                             */
void checkBeat(vector<float> instant_energy, vector<vector<float>> energy_history, vector<bool>& sub_band_beat)
{
    /* ------------------- DO STEP 1 ------------------- */ 

    // Initialize variable to hold max energy for each sub band and number of histories
    vector<float> max_energies;
    max_energies.resize(TOTAL_SUB_BANDS, 0);

    int num_histories = HISTORY_SECONDS * (int)(RATE / CHUNK_SIZE);

    // Looping through energy history
    for (int i = 0; i < TOTAL_SUB_BANDS; i++)
    {
        // Find the max energy for the specifc sub band first
        for (int j = 0; j < num_histories; j++)
        {
            max_energies[i] = max(max_energies[i], energy_history[j][i]);
        }

        // Now normalize each of the sub band values
        for (int j = 0; j < num_histories; j++)
        {
            energy_history[j][i] = energy_history[j][i] / max_energies[i];
        }
    }

    // Normalize each instant energy per sub band
    for (int i = 0; i < TOTAL_SUB_BANDS; i++)
    {
        instant_energy[i] = instant_energy[i] / max_energies[i];
    }


    /* ------------------- DO STEP 2 ------------------- */ 

    // Calculate the thresholds of each sub band based on energy history
    vector<float> thresholds;
    thresholds.resize(TOTAL_SUB_BANDS, 0);

    vector<float> average_energies;
    average_energies.resize(TOTAL_SUB_BANDS, 0);

    for (int i = 0; i < TOTAL_SUB_BANDS; i++)
    {
        for (int j = 0; j < num_histories; j++)
        {
            average_energies[i] += energy_history[j][i];
        }
        average_energies[i] = average_energies[i] / num_histories;

        for (int j = 0; j < num_histories; j++)
        {
            thresholds[i] += pow(energy_history[j][i] - average_energies[i], 2);
        }    
        thresholds[i] = thresholds[i] / num_histories;
        thresholds[i] = 15.0 * thresholds[i] + 1.4;
    }

    /* ------------------- DO STEP 3 ------------------- */ 

    // Check if there is a beat for each sub band
    for (int i = 0; i < TOTAL_SUB_BANDS; i++)
    {
        if (instant_energy[i] > thresholds[i] * average_energies[i] / 1.15 || instant_energy[i] > 0.15)
        {
            sub_band_beat[i] = true;
        }
        else
        {
            sub_band_beat[i] = false;
        }
    }
}


/* ===========================================================================      *
 * Function :   Check if beat is within an acceptable range of previous beats       *
 * Input    :   Energy of current beat for a specifc sub band and beat history      *
 * Return   :   True if detected beat exceeds threshold, otherwise false            */
bool confirmBeat(float instant_energy, vector<float>& beat_history)
{
    // Find the maximum energy of previously detected beats
    float max_energy = 0;
    for (int i = 0; i < beat_history.size(); i++)
    {
        max_energy = max(max_energy, beat_history[i]);
    }

    // Normalize all beat history values
    vector<float> norm_beat_history;
    norm_beat_history.resize(beat_history.size(), 0);
    for (int i = 0; i < beat_history.size(); i++)
    {
        norm_beat_history[i] = beat_history[i] / max_energy;
    }

    // Calculate the average of the beat history
    float average_energy = 0;
    for (int i = 0; i < beat_history.size(); i++)
    {
        average_energy += norm_beat_history[i];
    }
    average_energy = average_energy / beat_history.size();

    // Calculate the variance of the beat history
    float variance = 0;
    for (int i = 0; i < beat_history.size(); i++)
    {
        variance += pow(norm_beat_history[i] - average_energy, 2);
    }
    variance = variance / beat_history.size();

    // Check if current beat exceeds the threshold
    if (instant_energy / max_energy > average_energy * variance * 0.64)
    {
        beat_history.erase(beat_history.begin());
        beat_history.push_back(instant_energy);
        return true;
    }
    else
    {
        return false;
    }
}


/* ===========================================================================      *
 * Function :   Calculate clap energy based on different sub band weights           *
 * Input    :   Instant energy                                                      *
 * Return   :   Clap energy as a float                                              */
float getClapEnergy(vector<float> instant_energy)
{
    return (1.2 * instant_energy[CLAP_RANGE_LOW] + 
            1.3 * instant_energy[CLAP_RANGE_LOW + 1] + 
            1.5 * instant_energy[CLAP_RANGE_LOW + 2] + 
            1.4 * instant_energy[CLAP_RANGE_LOW + 5] + 
            1.6 * instant_energy[CLAP_RANGE_LOW + 6] + 
            1.4 * instant_energy[CLAP_RANGE_LOW + 9] + 
            1.6 * instant_energy[CLAP_RANGE_LOW + 10]) / 10;
}


/* ========================== BEGIN MAIN FUNCTION ========================== */

int main()
{
    /* ------------------- SETTING UP THE PROGRAM ------------------- */

    // initialize PortAudio
    PaError err;
    err = Pa_Initialize();
    checkErr(err);

    // Set up input stream parameters
    PaStreamParameters inputParameters;
    PaStreamParameters outputParameters;

    inputParameters.device = Pa_GetDefaultInputDevice();
    inputParameters.channelCount = CHANNELS;
    inputParameters.sampleFormat = FORMAT;
    inputParameters.suggestedLatency = Pa_GetDeviceInfo( inputParameters.device )->defaultHighInputLatency ;
    inputParameters.hostApiSpecificStreamInfo = NULL;

    outputParameters.device = Pa_GetDefaultOutputDevice();
    outputParameters.channelCount = CHANNELS;
    outputParameters.sampleFormat = FORMAT;
    outputParameters.suggestedLatency = Pa_GetDeviceInfo( outputParameters.device )->defaultHighOutputLatency;
    outputParameters.hostApiSpecificStreamInfo = NULL;

    // Setup stream
    PaStream* stream;
    err = Pa_OpenStream(
            &stream,
            &inputParameters,
            &outputParameters,
            RATE,
            CHUNK_SIZE,
            paClipOff,
            NULL, 
            NULL ); 
    checkErr(err);

    // Make fft plan before starting stream so that input is not overflowed
    fftw_complex *input_data, *amplitude_data;
    fftw_plan plan;
    input_data = (fftw_complex*) fftw_malloc(sizeof(fftw_complex) * CHUNK_SIZE);
    amplitude_data = (fftw_complex*) fftw_malloc(sizeof(fftw_complex) * CHUNK_SIZE);
    plan = fftw_plan_dft_1d(CHUNK_SIZE, input_data, amplitude_data, FFTW_FORWARD, FFTW_PATIENT);


    // Start stream
    err = Pa_StartStream(stream);
    checkErr(err);

    /* ------------------- INITIALZE CALCULATION VARIABLES ------------------- */

    // Number of chunks processed
    int chunks_processed = 0;

    // Holds the audio data
    float soundAmplitudeBuffer[CHUNK_SIZE * CHANNELS];

    // Energy for each of 39 sub bands as a vector
    vector<float> instant_energy; 
    instant_energy.resize(TOTAL_SUB_BANDS, 0);

    // Energy history for HISTORY_SECONDS taken at RATE / CHUNK_SIZE times per second
    vector<vector<float>> energy_history;

    // Beat tracking variable for each sub band (true if there is a beat otherwise false)
    vector<bool> sub_band_beat;
    sub_band_beat.resize(TOTAL_SUB_BANDS, true);

    // Beat history for successfully detected bass and claps
    vector<vector<float>> beat_history;
    for (int i = 0; i < 2; i++)
    {
        beat_history.push_back({0});
        for (int j = 0; j < 9; j++)
        {
            beat_history[0].push_back(0);
        }
        beat_history.push_back({0});
        for (int j = 0; j < 4; j++)
        {
            beat_history[1].push_back(0);
        }
    }

    // Chunk/time trackers for when bass and claps occur. Also a special clap energy variable
    int bass_chunk = 0;
    int clap_chunk = 0;
    float clap_energy = 0;


    /* ------------------- START LOOPING THROUGH AUDIO DATA ------------------- */

    // Record audio for HISTORY_SECONDS to fill energy history
    cout << "History Recording Started..." << endl;
    fflush(stdout);
    while (chunks_processed < (HISTORY_SECONDS * (int)(RATE / CHUNK_SIZE)))
    {
        err = Pa_ReadStream(stream, soundAmplitudeBuffer, CHUNK_SIZE);
        checkErr(err);
        for (int i = 0; i < CHUNK_SIZE; i++)
        {
            input_data[i][REAL] = soundAmplitudeBuffer[i] * 100000;
            input_data[i][IMAG] = 0;
        }

        fftw_execute(plan);                                 //  1. Take FFT of audio data
        getInstantEnergy(amplitude_data, instant_energy);   //  2. Calculate energy of sub bands
        energy_history.push_back(instant_energy);           //  3. Append energy history

        chunks_processed++;
    }
    cout << "History Recording Ended..." << endl;
    fflush(stdout);

    // Record audio for the rest of RECORD_SECONDS
    cout << "Total Recording Started..." << endl;
    fflush(stdout);
    while (chunks_processed < (RECORD_SECONDS * (int)(RATE / CHUNK_SIZE)))
    {
        err = Pa_ReadStream(stream, soundAmplitudeBuffer, CHUNK_SIZE);
        checkErr(err);
        for (int i = 0; i < CHUNK_SIZE; i++)
        {
            input_data[i][REAL] = soundAmplitudeBuffer[i] * 100000;
            input_data[i][IMAG] = 0;
        }

        fftw_execute(plan);                                         //  1. Take FFT of audio data
        getInstantEnergy(amplitude_data, instant_energy);           //  2. Calculate energy of sub bands
        checkBeat(instant_energy, energy_history, sub_band_beat);   //  3. Check for a beat
        if (sub_band_beat[0])                                       //  4. Accuretly check bass
        {
            if (chunks_processed - bass_chunk > 4)
            {
                if (beat_history[0][9] > 0)
                {
                    if (confirmBeat(instant_energy[0], beat_history[0]))
                    {
                        cout << "Bass: " << chunks_processed << "   " << "Energy: " << instant_energy[0] << endl;
                        fflush(stdout);
                        bass_chunk = chunks_processed;
                    }
                }
                else
                {
                    // Find the first index that is 0 in beat history
                    int i = 0;
                    while (beat_history[0][i] > 0)
                    {
                        i++;
                    }
                    beat_history[0][i] = instant_energy[0];
                }
            }
        }

        clap_energy = getClapEnergy(instant_energy);                               //  5. Accuretly check claps
        if (sub_band_beat[CLAP_RANGE_LOW] && sub_band_beat[CLAP_RANGE_LOW + 1] && sub_band_beat[CLAP_RANGE_LOW + 2] && sub_band_beat[CLAP_RANGE_LOW + 5] && sub_band_beat[CLAP_RANGE_LOW + 6] && sub_band_beat[CLAP_RANGE_LOW + 9] && sub_band_beat[CLAP_RANGE_LOW + 10])                                   
        {
            if (chunks_processed - clap_chunk > 4)
            {
                if (beat_history[1][4] > 0)
                {
                    if (confirmBeat(clap_energy * 1.6, beat_history[1]))
                    {
                        cout << "Clap: " << chunks_processed << "   " << "Energy: " << clap_energy << endl;
                        fflush(stdout);
                        clap_chunk = chunks_processed;
                    }
                }
                else
                {
                    // Find the first index that is 0 in beat history
                    int i = 0;
                    while (beat_history[1][i] > 0)
                    {
                        i++;
                    }
                    beat_history[1][i] = clap_energy;
                }
            }
        }
                                                                                   //  6. Reset beat history every 20 seconds
        if (chunks_processed - bass_chunk > (int)(20 * RATE / CHUNK_SIZE) || chunks_processed - clap_chunk > (int)(20 * RATE / CHUNK_SIZE))
        {
            for (int i = 0; i < 10; i++)
            {
                beat_history[0][i] = 0;
            }
            for (int i = 0; i < 5; i++)
            {
                beat_history[1][i] = 0;
            }
        }

        energy_history.erase(energy_history.begin());                               //  7. Update energy history
        energy_history.push_back(instant_energy);

        chunks_processed++;                                                         //  8. Update chunk count and proceed to next
    }
    cout << "Total Recording Ending..." << endl;
    fflush(stdout);


    /* -------------------  CLEANUP ------------------- */

    err = Pa_StopStream( stream );
    checkErr(err);

    err = Pa_CloseStream( stream );
    checkErr(err);

    Pa_Terminate();

    fftw_destroy_plan(plan);
    fftw_free(input_data); fftw_free(amplitude_data);

    return 0;
}