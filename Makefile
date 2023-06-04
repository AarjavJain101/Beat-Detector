Beat_Tracking: Beat_Tracking.cpp 
	g++ -o Beat_Tracking Beat_Tracking.cpp BTrack-1.0.4/src/BTrack.cpp BTrack-1.0.4/src/OnsetDetectionFunction.cpp -DUSE_FFTW -I BTrack-1.0.4/src -I BTrack-1.0.4/libs/kiss_fft130 `pkg-config --cflags --libs fftw3 portaudio-2.0 samplerate`
