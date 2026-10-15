import {useEffect, useRef, useState} from 'react';
import * as THREE from 'three';
import type {AudioAnalysis} from './audio';
import type {AudioFrame, VisualizerPreset} from './presets';

interface Props {
    audio: HTMLAudioElement;
    analysis: AudioAnalysis;
    preset: VisualizerPreset;
    intensity: number;
    motion: boolean;
    quality: 'low' | 'high';
}

export default function VisualizerCanvas({audio, analysis, preset, intensity, motion, quality}: Props) {
    const containerRef = useRef<HTMLDivElement>(null);
    const settings = useRef({intensity, motion});
    const redraw = useRef<(() => void) | null>(null);
    const [error, setError] = useState('');
    useEffect(() => {
        settings.current = {intensity, motion};
        redraw.current?.();
    }, [intensity, motion]);

    useEffect(() => {
        const container = containerRef.current;
        if (!container) return;
        const canvas = document.createElement('canvas');
        canvas.style.cssText = 'width:100%;height:100%;display:block';
        canvas.setAttribute('aria-label', `${preset.name} music visualization`);
        container.appendChild(canvas);
        let renderer: THREE.WebGLRenderer;
        try {
            renderer = new THREE.WebGLRenderer({canvas, antialias: quality === 'high', powerPreference: 'low-power'});
        } catch (cause) {
            canvas.remove();
            setError(`3D rendering is unavailable. Music controls still work. ${String(cause)}`);
            return;
        }
        setError('');
        renderer.setPixelRatio(Math.min(window.devicePixelRatio, quality === 'low' ? 1 : 1.5));
        renderer.setClearColor('#050914');
        const scene = new THREE.Scene();
        const camera = new THREE.PerspectiveCamera(55, 1, 0.1, 100);
        camera.position.z = 8;
        const active = preset.create();
        scene.add(active.root);
        const frame: AudioFrame = {
            spectrum: new Uint8Array(analysis.analyser.frequencyBinCount),
            waveform: new Uint8Array(analysis.analyser.fftSize),
            bass: 0, energy: 0, time: 0, ...settings.current,
        };
        let request = 0;
        let previous = 0;
        let lost = false;
        let visible = true;
        const render = (now: number) => {
            request = 0;
            if (document.hidden || lost || !visible) return;
            if (now - previous >= (quality === 'low' ? 1000 / 30 : 1000 / 60) || audio.paused) {
                frame.time += previous && !audio.paused ? Math.min((now - previous) / 1000, 0.1) : 0;
                previous = now;
                analysis.analyser.getByteFrequencyData(frame.spectrum);
                analysis.analyser.getByteTimeDomainData(frame.waveform);
                frame.bass = frame.spectrum.subarray(1, 12).reduce((sum, value) => sum + value, 0) / (11 * 255);
                frame.energy = frame.spectrum.reduce((sum, value) => sum + value, 0) / (frame.spectrum.length * 255);
                Object.assign(frame, settings.current);
                active.update(frame);
                renderer.render(scene, camera);
            }
            if (!audio.paused && !audio.ended) request = requestAnimationFrame(render);
        };
        const wake = () => {
            cancelAnimationFrame(request);
            previous = 0;
            request = requestAnimationFrame(render);
        };
        redraw.current = wake;
        const visibility = new IntersectionObserver(([entry]) => {
            visible = entry.isIntersecting;
            wake();
        });
        visibility.observe(canvas);
        const resize = new ResizeObserver(() => {
            const {width, height} = canvas.getBoundingClientRect();
            renderer.setSize(width, height, false);
            camera.aspect = width / Math.max(height, 1);
            camera.position.z = 8 / Math.min(Math.max(camera.aspect, 0.2), 1);
            camera.updateProjectionMatrix();
            wake();
        });
        const contextLost = (event: Event) => {
            event.preventDefault();
            lost = true;
            cancelAnimationFrame(request);
            setError('The graphics context was lost. Close and reopen the visualizer to retry.');
        };
        resize.observe(canvas);
        canvas.addEventListener('webglcontextlost', contextLost);
        audio.addEventListener('play', wake);
        audio.addEventListener('pause', wake);
        audio.addEventListener('seeked', wake);
        document.addEventListener('visibilitychange', wake);
        wake();
        return () => {
            redraw.current = null;
            cancelAnimationFrame(request);
            resize.disconnect();
            visibility.disconnect();
            canvas.removeEventListener('webglcontextlost', contextLost);
            audio.removeEventListener('play', wake);
            audio.removeEventListener('pause', wake);
            audio.removeEventListener('seeked', wake);
            document.removeEventListener('visibilitychange', wake);
            active.dispose();
            renderer.dispose();
            renderer.forceContextLoss();
            canvas.remove();
        };
    }, [audio, analysis, preset, quality]);

    return <>
        <div ref={containerRef} style={{width: '100%', height: '100%'}} />
        {error && <p role="alert" style={{position: 'absolute', top: '25%', left: '10%', right: '10%'}}>{error}</p>}
    </>;
}
