THREADS=8

if [ ! -d fftw-3.3.10 ] && [ ! -d portaudio ]; then 
	curl https://www.fftw.org/fftw-3.3.10.tar.gz | tar --extract -z -f - 
	curl http://files.portaudio.com/archives/pa_stable_v190700_20210406.tgz | tar --extract -z -f - 
	cd fftw-3.3.10
	./configure
	make -j${THREADS} 
	cd ../portaudio
	./configure
	make -j${THREADS} 
	cd ..
fi

if [ -f portaudio/lib/.libs/libportaudio.a ]; then 
	PORTAUDIO_LIB="libportaudio.a" 
else 
	PORTAUDIO_LIB="libportaudio.dll.a" 
fi

g++ -o Beat_Tracking Beat_Tracking.cpp -Iportaudio/include -Ifftw-3.3.10/api -pthread -Lportaudio/lib/.libs -Lfftw-3.3.10/.libs -l:${PORTAUDIO_LIB} -lm -l:libfftw3.a