# Bass-Detector with [Rhys Byers](https://github.com/rhys-b)
* Download and Run the Beat_Tracking.exe to use the application. ** Windows Only**
* This is a Python and C++ program that detects bass and claps and hi-hats in music. I created and tested my algorithm (not using CNN or other machine learning) using rap and hip-hop music and as such the algorithm has the greatest accuracy when listening to these genres.
* The "Beat_Tracking" file is the C++ version of the Python program (without video) that is used to make the Arduino code

## Usage
* The Python file titled "Beat_Detector_No_Video.py" will print that bass or claps are detected in the terminal whenever the algorithm captures it
* The Python file titled "Beat_Detector_With_Video.py" will print that bass or claps are detected in the terminal whenever the algorithm captures it AND will fill a folder titled "Frames_FFT" with the plot of the FFT zoomed into the bass region (you may need to play around with the y-range in the makePlotsWithThreshold function to actually see it).
* The Python file titled "Light_Room.py" will open a window (fullscreen and max bright for best effects). When you play music it will flash colors. An example of use is to connect your screen to a larger TV screen or projector to fill a whole room with the changing colors.
* To compile the C++ file you will need a UNIX-like environment. Clone the repository and run `./build.sh`

## Dependencies
* This program will use ffmpeg (you will need to install this) to create a video out of both the frames in the folder and the audio data collected and stored as a .wav file in the "Videos" folder. Note this is only for the 'with video' program
* You will need to install pyaudio to use the import.
* The C++ make file will take care of the dependencies. These include FFTW3 and portaudio.

## Parameters
Parameters such as the recording time are adjustable at the top of both these programs (currently set to 20 seconds).

## Example
For a sample of my bass detector take a look at the video already in the Videos folder. It is a 20-second clip of the song "Millions" by Young Thug. The blue line is the cubed amplitude of the FFT output and the orange line is the threshold that must be passed for bass to be detected.

## Note
Please make sure that all the folders are present together with the video Python file to run.
