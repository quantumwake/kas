// Procedural sound effects using Web Audio API
let audioCtx = null;

function getAudioContext() {
  if (!audioCtx) {
    audioCtx = new (window.AudioContext || window.webkitAudioContext)();
  }
  return audioCtx;
}

// Play a simple beep/click
export function playClick() {
  try {
    const ctx = getAudioContext();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.frequency.value = 800;
    gain.gain.setValueAtTime(0.1, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.1);
    osc.start(ctx.currentTime);
    osc.stop(ctx.currentTime + 0.1);
  } catch (e) { /* ignore */ }
}

// Play construction sound
export function playBuild() {
  try {
    const ctx = getAudioContext();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = 'square';
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.frequency.setValueAtTime(200, ctx.currentTime);
    osc.frequency.linearRampToValueAtTime(400, ctx.currentTime + 0.15);
    gain.gain.setValueAtTime(0.08, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.2);
    osc.start(ctx.currentTime);
    osc.stop(ctx.currentTime + 0.2);
  } catch (e) { /* ignore */ }
}

// Play error sound
export function playError() {
  try {
    const ctx = getAudioContext();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = 'sawtooth';
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.frequency.value = 150;
    gain.gain.setValueAtTime(0.1, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.3);
    osc.start(ctx.currentTime);
    osc.stop(ctx.currentTime + 0.3);
  } catch (e) { /* ignore */ }
}

// Play cash sound
export function playCash() {
  try {
    const ctx = getAudioContext();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = 'sine';
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.frequency.setValueAtTime(1200, ctx.currentTime);
    osc.frequency.exponentialRampToValueAtTime(1800, ctx.currentTime + 0.1);
    gain.gain.setValueAtTime(0.08, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.15);
    osc.start(ctx.currentTime);
    osc.stop(ctx.currentTime + 0.15);
  } catch (e) { /* ignore */ }
}

// Play engine sound (loop)
export function createEngineLoop(cls) {
  try {
    const ctx = getAudioContext();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.connect(gain);
    gain.connect(ctx.destination);

    if (cls === 'train') {
      osc.type = 'sawtooth';
      osc.frequency.value = 80;
    } else if (cls === 'road') {
      osc.type = 'square';
      osc.frequency.value = 120;
    } else if (cls === 'air') {
      osc.type = 'sine';
      osc.frequency.value = 300;
    } else {
      osc.type = 'triangle';
      osc.frequency.value = 60;
    }

    gain.gain.value = 0.02;
    osc.start();
    return { stop: () => { osc.stop(); osc.disconnect(); } };
  } catch (e) {
    return { stop: () => {} };
  }
}

// Simple background music
let musicInterval = null;
let musicNotes = [];

export function startMusic() {
  stopMusic();
  // Simple melody notes
  const melody = [262, 294, 330, 349, 392, 349, 330, 294];
  let noteIdx = 0;

  musicInterval = setInterval(() => {
    try {
      const ctx = getAudioContext();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = 'triangle';
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.frequency.value = melody[noteIdx % melody.length];
      gain.gain.setValueAtTime(0.03, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.4);
      osc.start(ctx.currentTime);
      osc.stop(ctx.currentTime + 0.4);
      noteIdx++;
    } catch (e) { /* ignore */ }
  }, 500);
}

export function stopMusic() {
  if (musicInterval) {
    clearInterval(musicInterval);
    musicInterval = null;
  }
}

// Enable audio on user interaction
export function initAudio() {
  getAudioContext();
}
