"""Generate an original, quiet electronic bed; no external audio assets."""
import wave
from pathlib import Path
import numpy as np


def generate_music(path,duration,sample_rate=22050):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    frequencies=[220.0,261.6256,329.6276,293.6648]
    with wave.open(str(path),'wb') as output:
        output.setnchannels(1);output.setsampwidth(2);output.setframerate(sample_rate)
        count=round(duration*sample_rate)
        for start in range(0,count,sample_rate):
            t=(start+np.arange(min(sample_rate,count-start)))/sample_rate
            index=(np.floor(t/.625).astype(int)%len(frequencies))
            frequency=np.array(frequencies)[index]
            phase=t%.625
            envelope=np.sin(np.pi*np.minimum(phase/.12,1))**2*np.exp(-phase*4)
            # A sine arpeggio and a very soft harmonic pad.
            signal=.045*np.sin(2*np.pi*frequency*phase)*envelope
            signal+=.016*(np.sin(2*np.pi*110*t)+.5*np.sin(2*np.pi*164.8138*t))
            signal*=np.minimum(1,t/1.2)*np.minimum(1,(duration-t)/1.2)
            output.writeframes(np.clip(signal*32767,-32768,32767).astype('<i2').tobytes())
    return path
