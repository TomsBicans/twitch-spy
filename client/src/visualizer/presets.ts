import * as THREE from 'three';

export interface AudioFrame {
    spectrum: Uint8Array<ArrayBuffer>;
    sampleRate: number;
    waveform: Uint8Array<ArrayBuffer>;
    bass: number;
    energy: number;
    time: number;
    intensity: number;
    motion: boolean;
}

export interface VisualizerScene {
    root: THREE.Object3D;
    resize?: (width: number, height: number) => void;
    update: (frame: AudioFrame) => void;
    setColor: (color?: string) => void;
    dispose: () => void;
}

export interface VisualizerPreset {
    id: string;
    name: string;
    description: string;
    create: () => VisualizerScene;
}

function artworkColor(value: string): THREE.Color {
    const color = new THREE.Color(value);
    const hsl = {h: 0, s: 0, l: 0};
    color.getHSL(hsl);
    // Keep dark artwork visible while preserving its hue and neutral tones.
    return color.setHSL(hsl.h, hsl.s, Math.max(hsl.l, 0.3));
}

function createSpectrumBars(): VisualizerScene {
    const count = 48;
    const width = 6.8;
    const baseline = -1.8;
    const root = new THREE.Group();
    const geometry = new THREE.PlaneGeometry(width / count * 0.76, 1);
    const material = new THREE.MeshBasicMaterial({color: '#ffffff'});
    const peakMaterial = new THREE.MeshBasicMaterial({color: '#e5e0ff'});
    const bars = new THREE.InstancedMesh(geometry, material, count);
    const peaks = new THREE.InstancedMesh(geometry, peakMaterial, count);
    const levels = new Float32Array(count);
    const peakLevels = new Float32Array(count);
    const transform = new THREE.Object3D();
    const color = new THREE.Color();
    const highlight = new THREE.Color('#ffffff');
    let previousTime: number | undefined;
    bars.frustumCulled = false;
    peaks.frustumCulled = false;
    bars.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
    peaks.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
    root.add(bars, peaks);
    return {
        root,
        resize: (viewportWidth, viewportHeight) => {
            root.scale.set(viewportWidth * 0.92 / width, viewportHeight * 0.88 / 3.6, 1);
        },
        setColor: value => {
            const base = value ? artworkColor(value) : null;
            for (let index = 0; index < count; index++) {
                if (base) color.copy(base).lerp(highlight, 0.12 + index / (count - 1) * 0.4);
                else color.setHSL(0.48 + index / (count - 1) * 0.26, 0.75, 0.62);
                bars.setColorAt(index, color);
            }
            if (bars.instanceColor) bars.instanceColor.needsUpdate = true;
            peakMaterial.color.copy(base ? base.clone().lerp(highlight, 0.7) : highlight);
        },
        update: ({spectrum, sampleRate, time, intensity}) => {
            const elapsed = previousTime === undefined ? 1 / 30 : Math.max(0, Math.min(time - previousTime, 0.1));
            previousTime = time;
            const binWidth = sampleRate / (spectrum.length * 2);
            const minimum = Math.max(30, binWidth);
            const maximum = Math.min(18000, sampleRate / 2);
            for (let index = 0; index < count; index++) {
                const lower = minimum * Math.pow(maximum / minimum, index / count);
                const upper = minimum * Math.pow(maximum / minimum, (index + 1) / count);
                const start = Math.min(spectrum.length - 1, Math.max(1, Math.floor(lower / binWidth)));
                const end = Math.min(spectrum.length, Math.max(start + 1, Math.ceil(upper / binWidth)));
                let amplitude = 0;
                for (let bin = start; bin < end; bin++) amplitude = Math.max(amplitude, spectrum[bin] / 255);
                const target = Math.min(1, amplitude * intensity);
                const smoothing = 1 - Math.exp(-elapsed * (target > levels[index] ? 28 : 8));
                levels[index] += (target - levels[index]) * smoothing;
                peakLevels[index] = Math.max(levels[index], peakLevels[index] - elapsed * 0.22);
                const height = 0.025 + levels[index] * 3.5;
                const horizontal = -width / 2 + (index + 0.5) * width / count;
                transform.position.set(horizontal, baseline + height / 2, 0);
                transform.scale.set(1, height, 1);
                transform.updateMatrix();
                bars.setMatrixAt(index, transform.matrix);
                transform.position.set(horizontal, baseline + 0.05 + peakLevels[index] * 3.5, 0);
                transform.scale.set(1, 0.025, 1);
                transform.updateMatrix();
                peaks.setMatrixAt(index, transform.matrix);
            }
            bars.instanceMatrix.needsUpdate = true;
            peaks.instanceMatrix.needsUpdate = true;
        },
        dispose: () => { geometry.dispose(); material.dispose(); peakMaterial.dispose(); bars.dispose(); peaks.dispose(); },
    };
}

function createHalo(): VisualizerScene {
    const root = new THREE.Group();
    const geometry = new THREE.BoxGeometry(0.065, 1, 0.065);
    const material = new THREE.MeshBasicMaterial({color: '#8c7cff'});
    const bars = new THREE.InstancedMesh(geometry, material, 128);
    const dummy = new THREE.Object3D();
    const color = new THREE.Color();
    for (let i = 0; i < 128; i++) bars.setColorAt(i, color.setHSL(i / 190 + 0.45, 0.8, 0.65));
    bars.frustumCulled = false;
    root.add(bars);
    return {
        root,
        setColor: value => {
            material.color.set(value ? '#ffffff' : '#8c7cff');
            const base = value ? artworkColor(value) : null;
            const highlight = new THREE.Color('#ffffff');
            for (let i = 0; i < 128; i++) {
                if (base) color.copy(base).lerp(highlight, i / 127 * 0.45);
                else color.setHSL(i / 190 + 0.45, 0.8, 0.65);
                bars.setColorAt(i, color);
            }
            if (bars.instanceColor) bars.instanceColor.needsUpdate = true;
        },
        update: ({spectrum, bass, time, intensity, motion}) => {
            for (let i = 0; i < 128; i++) {
                const angle = i / 128 * Math.PI * 2;
                const bin = Math.floor(Math.pow(i / 127, 2) * (spectrum.length - 1));
                const height = 0.08 + spectrum[bin] / 255 * intensity * 1.8;
                dummy.position.set(Math.cos(angle) * 2, Math.sin(angle) * 2, 0);
                dummy.rotation.z = angle - Math.PI / 2;
                dummy.scale.set(1, height, 1 + bass * 4);
                dummy.updateMatrix();
                bars.setMatrixAt(i, dummy.matrix);
            }
            bars.instanceMatrix.needsUpdate = true;
            root.rotation.set(motion ? Math.sin(time * 0.2) * 0.4 : 0.25, 0.2, motion ? time * 0.08 : 0);
        },
        dispose: () => { geometry.dispose(); material.dispose(); bars.dispose(); },
    };
}

function createTerrain(): VisualizerScene {
    const geometry = new THREE.PlaneGeometry(9, 8, 64, 48);
    geometry.rotateX(-Math.PI / 2);
    const material = new THREE.MeshBasicMaterial({color: '#54e5d0', wireframe: true, transparent: true, opacity: 0.65});
    const root = new THREE.Mesh(geometry, material);
    root.position.set(0, -1, -1);
    root.rotation.x = 0.25;
    const positions = geometry.getAttribute('position');
    return {
        root,
        setColor: value => { material.color.copy(value ? artworkColor(value) : new THREE.Color('#54e5d0')); },
        update: ({spectrum, waveform, time, intensity, motion}) => {
            for (let i = 0; i < positions.count; i++) {
                const x = positions.getX(i);
                const z = positions.getZ(i);
                const bin = Math.floor(Math.abs(x) / 4.5 * 220);
                const amplitude = spectrum[bin] / 255 * intensity;
                const wave = (waveform[i % waveform.length] - 128) / 128;
                positions.setY(i, Math.sin(z * 1.8 + (motion ? time * 1.5 : 0)) * amplitude + wave * intensity * 0.35);
            }
            positions.needsUpdate = true;
        },
        dispose: () => { geometry.dispose(); material.dispose(); },
    };
}

function createOrbit(): VisualizerScene {
    const count = 2400;
    const geometry = new THREE.BufferGeometry();
    const coordinates = new Float32Array(count * 3);
    const colors = new Float32Array(count * 3);
    const color = new THREE.Color();
    for (let i = 0; i < count; i++) {
        color.setHSL(0.53 + i / count * 0.35, 0.8, 0.7).toArray(colors, i * 3);
    }
    geometry.setAttribute('position', new THREE.BufferAttribute(coordinates, 3));
    geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
    const material = new THREE.PointsMaterial({size: 0.025, vertexColors: true, transparent: true,
        opacity: 0.85, blending: THREE.AdditiveBlending, depthWrite: false});
    const root = new THREE.Points(geometry, material);
    root.frustumCulled = false;
    return {
        root,
        setColor: value => {
            const base = value ? artworkColor(value) : null;
            const highlight = new THREE.Color('#ffffff');
            for (let i = 0; i < count; i++) {
                if (base) color.copy(base).lerp(highlight, i / count * 0.45);
                else color.setHSL(0.53 + i / count * 0.35, 0.8, 0.7);
                color.toArray(colors, i * 3);
            }
            geometry.getAttribute('color').needsUpdate = true;
        },
        update: ({spectrum, bass, energy, time, intensity, motion}) => {
            for (let i = 0; i < count; i++) {
                const y = 1 - i / (count - 1) * 2;
                const radius = (2 + spectrum[i % 400] / 255 * intensity) * Math.sqrt(1 - y * y);
                const angle = i * 2.399963;
                coordinates[i * 3] = Math.cos(angle) * radius;
                coordinates[i * 3 + 1] = y * (2 + bass * intensity);
                coordinates[i * 3 + 2] = Math.sin(angle) * radius;
            }
            geometry.getAttribute('position').needsUpdate = true;
            root.rotation.set(0.2, motion ? time * 0.12 : 0, motion ? Math.sin(time * 0.15) * 0.2 : 0);
            material.size = 0.022 + energy * intensity * 0.035;
        },
        dispose: () => { geometry.dispose(); material.dispose(); },
    };
}

export const presets: readonly VisualizerPreset[] = [
    {id: 'bars', name: 'Spectrum bars', description: 'Rising frequency bars, from bass on the left to highs on the right.', create: createSpectrumBars},
    {id: 'halo', name: 'Spectrum halo', description: 'A rotating crown of frequency and color.', create: createHalo},
    {id: 'terrain', name: 'Wave terrain', description: 'A wireframe landscape shaped by sound.', create: createTerrain},
    {id: 'orbit', name: 'Particle orbit', description: 'An expanding constellation of sound.', create: createOrbit},
];
