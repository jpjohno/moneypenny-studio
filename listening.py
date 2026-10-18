"""Private warm Whisper server owned by this studio, with local Vosk fallback."""
import atexit
import io
from pathlib import Path
import shutil
import socket
import subprocess
import threading
import time
import wave
import requests
from speech import voice_config, transcribe as vosk_transcribe


class Listening:
    def __init__(self):
        self.process = None
        self.url = None
        self.lock = threading.Lock()
        atexit.register(self.close)

    def available(self):
        config=voice_config()
        return bool((shutil.which('whisper-server') or config.get('whisper_server')) and Path(config.get('whisper_model','__missing__')).is_file())

    def close(self):
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:self.process.kill()
        self.process=None

    def warm(self):
        if not self.available():return False
        with self.lock:
            if self.process and self.process.poll() is None:return True
            config=voice_config()
            with socket.socket() as sock:
                sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
            self.url=f'http://127.0.0.1:{port}'
            self.process=subprocess.Popen([
                config.get('whisper_server') or shutil.which('whisper-server'),
                '-m',config['whisper_model'],'--host','127.0.0.1','--port',str(port),
                '-t','4','-l','en','-nc','-sns',
            ],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            for _ in range(150):
                if self.process.poll() is not None:break
                try:
                    if requests.get(self.url+'/',timeout=.25).status_code<500:return True
                except requests.RequestException:pass
                time.sleep(.1)
            self.close()
            return False

    def transcribe(self,pcm):
        if not self.available():return vosk_transcribe(pcm)
        if not self.warm():raise ValueError('Whisper could not start. Check the listening setup.')
        output=io.BytesIO()
        with wave.open(output,'wb') as recording:
            recording.setparams((1,2,16000,0,'NONE','not compressed'));recording.writeframes(pcm)
        with self.lock:
            response=requests.post(self.url+'/inference',files={'file':('speech.wav',output.getvalue(),'audio/wav')},
                data={'response_format':'json','temperature':'0','language':'en'},timeout=45)
        response.raise_for_status()
        value=response.json().get('text','').strip()
        # Non-speech labels are not conversation commands.
        if value.startswith('[') and value.endswith(']'):return ''
        return value
