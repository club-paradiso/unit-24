/** Converts user-selected session recording to uncompressed 16 kHz mono WAV for Azure REST. */
export async function audioToWav16k(blob: Blob): Promise<Blob> {
  if (!blob.size || blob.size > 5_000_000) throw new Error("AUDIO_TOO_LARGE");
  const Ctor = window.AudioContext;
  if (!Ctor) throw new Error("AUDIO_DECODER_UNSUPPORTED");
  const context = new Ctor();
  let buffer: AudioBuffer;
  try {
    buffer = await context.decodeAudioData(await blob.arrayBuffer());
  } catch {
    throw new Error("AUDIO_DECODE_FAILED");
  } finally {
    await context.close();
  }
  if (!Number.isFinite(buffer.duration) || buffer.duration <= 0.08 || buffer.duration > 22) {
    throw new Error("AUDIO_DURATION_INVALID");
  }
  const rate = 16000;
  const frames = Math.floor(buffer.duration * rate);
  const output = new ArrayBuffer(44 + frames * 2);
  const view = new DataView(output);
  const write = (offset: number, text: string) => {
    for (let i = 0; i < text.length; i++) view.setUint8(offset + i, text.charCodeAt(i));
  };
  write(0, "RIFF"); view.setUint32(4, output.byteLength - 8, true);
  write(8, "WAVE"); write(12, "fmt ");
  view.setUint32(16, 16, true); view.setUint16(20, 1, true);
  view.setUint16(22, 1, true); view.setUint32(24, rate, true);
  view.setUint32(28, rate * 2, true); view.setUint16(32, 2, true);
  view.setUint16(34, 16, true); write(36, "data");
  view.setUint32(40, frames * 2, true);
  const sourceRate = buffer.sampleRate;
  const channels = Array.from({ length: buffer.numberOfChannels }, (_, i) => buffer.getChannelData(i));
  for (let i = 0; i < frames; i++) {
    const position = i * sourceRate / rate;
    const index = Math.floor(position);
    const frac = position - index;
    let sample = 0;
    for (const channel of channels) {
      const a = channel[Math.min(index, channel.length - 1)] ?? 0;
      const b = channel[Math.min(index + 1, channel.length - 1)] ?? 0;
      sample += a + (b - a) * frac;
    }
    sample = Math.max(-1, Math.min(1, sample / channels.length));
    view.setInt16(44 + i * 2, sample < 0 ? sample * 0x8000 : sample * 0x7fff, true);
  }
  return new Blob([output], { type: "audio/wav" });
}
