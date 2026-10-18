// Explicit recording with local transcription; never an always-on microphone.
export class Recorder {
  constructor() { this.active = false; this.frames = []; }
  async start(onLimit) {
    this.stream = await navigator.mediaDevices.getUserMedia({audio: {channelCount:1, echoCancellation:true, noiseSuppression:true}});
    try {
      this.context = new AudioContext();
      await this.context.audioWorklet.addModule('/static/record-worklet.js');
      this.source = this.context.createMediaStreamSource(this.stream);
      this.node = new AudioWorkletNode(this.context, 'studio-recorder');
      this.frames = [];
      this.node.port.onmessage = e => { if (this.active) this.frames.push(e.data); };
      this.source.connect(this.node);
      const silent = this.context.createGain(); silent.gain.value = 0;
      this.node.connect(silent); silent.connect(this.context.destination);
      await this.context.resume();
      this.active = true;
      this.timer = setTimeout(onLimit, 29000);
    } catch (e) { this.release(); throw e; }
  }
  release() {
    clearTimeout(this.timer); this.active = false;
    this.stream?.getTracks().forEach(track => track.stop());
    this.node?.disconnect(); this.source?.disconnect();
    this.context?.close().catch(() => {});
  }
  cancel() { this.release(); this.frames = []; }
  async finish() {
    const rate = this.context.sampleRate;
    this.release();
    const size = this.frames.reduce((sum, frame) => sum + frame.length, 0);
    if (!size) throw new Error('No audio was captured. Please try again.');
    const offline = new OfflineAudioContext(1, Math.min(480000, Math.ceil(size * 16000 / rate)), 16000);
    const input = offline.createBuffer(1, size, rate);
    let offset = 0;
    for (const frame of this.frames) { input.copyToChannel(frame, 0, offset); offset += frame.length; }
    this.frames = [];
    const source = offline.createBufferSource(); source.buffer = input;
    source.connect(offline.destination); source.start();
    const output = await offline.startRendering();
    const samples = output.getChannelData(0);
    const wav = new ArrayBuffer(44 + samples.length * 2), view = new DataView(wav);
    const string = (offset, value) => { for(let i=0;i<value.length;i++) view.setUint8(offset+i, value.charCodeAt(i)); };
    string(0,'RIFF'); view.setUint32(4,36+samples.length*2,true); string(8,'WAVE'); string(12,'fmt ');
    view.setUint32(16,16,true); view.setUint16(20,1,true); view.setUint16(22,1,true);
    view.setUint32(24,16000,true); view.setUint32(28,32000,true); view.setUint16(32,2,true); view.setUint16(34,16,true);
    string(36,'data'); view.setUint32(40,samples.length*2,true);
    for(let i=0;i<samples.length;i++) view.setInt16(44+i*2,Math.max(-1,Math.min(1,samples[i])) * (samples[i]<0?32768:32767),true);
    return wav;
  }
}
