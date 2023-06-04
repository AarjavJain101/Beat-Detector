Beat_Tracking: Beat_Tracking.cpp 
	g++ -o Beat_Tracking Beat_Tracking.cpp -DUSE_FFTW `pkg-config --cflags --libs fftw3 portaudio-2.0`

DEPS: 
	curl https://www.fftw.org/fftw-3.3.10.tar.gz | tar