# Bass-Detector
This is a python program that detects bass in music. I created and tested my algorithm (not using CNN or other machine learning) using rap and hip-hop music. 

The python file titled "Bass_Detector_No_Video.py" will print that bass is detected in the terminal whenever the algorthim captures it
The python file titled "Bass_Detector_With_Video.py" will print that bass is detected in the terminal whenever the algorthim captures it AND will fill a folder titled "Frames_FFT" with the plot of the FFT zoomed into the bass region (you may need to play around with the y-range in the makePlotsWithThreshold function to actually see it). Also, this program will then use ffmpeg (you will need to install this) to create a video out of both the frames in the folder and the audio data collected and stored as a .wav file in the "Videos" folder.

Parameters such as the recording time are adjustable at the top of both these progrmas (currently set to 20 seconds).

For a sample of my bass detector take a look at the video already in the Videos folder. It is a 20 second clip of the song "Millions" by Young Thug. The blue line is the cubed amplitude of the fft output and the orange line is the threshold that must be passed for bass to be detected.
