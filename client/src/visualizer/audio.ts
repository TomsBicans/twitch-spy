export interface AudioAnalysis {
    context: AudioContext;
    analyser: AnalyserNode;
    source: MediaElementAudioSourceNode;
}

export interface VisualizerPlayback {
    audio: HTMLAudioElement;
    analysis: AudioAnalysis;
}

// A media element can only be attached to one source during its lifetime.
const analyses = new WeakMap<HTMLAudioElement, AudioAnalysis>();

export function getAudioAnalysis(audio: HTMLAudioElement): AudioAnalysis {
    const existing = analyses.get(audio);
    if (existing) return existing;
    const context = new AudioContext();
    try {
        const analyser = context.createAnalyser();
        analyser.fftSize = 2048;
        analyser.smoothingTimeConstant = 0.8;
        const source = context.createMediaElementSource(audio);
        source.connect(context.destination);
        source.connect(analyser);
        const analysis = {context, analyser, source};
        analyses.set(audio, analysis);
        return analysis;
    } catch (error) {
        void context.close();
        throw error;
    }
}

export function releaseAudioAnalysis(audio: HTMLAudioElement): void {
    const analysis = analyses.get(audio);
    if (!analysis) return;
    analysis.source.disconnect();
    analysis.analyser.disconnect();
    void analysis.context.close();
    analyses.delete(audio);
}
