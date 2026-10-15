import * as THREE from 'three';

export interface AudioFrame {
    spectrum: Uint8Array<ArrayBuffer>;
    waveform: Uint8Array<ArrayBuffer>;
    bass: number;
    energy: number;
    time: number;
    intensity: number;
    motion: boolean;
}

export interface VisualizerScene {
    root: THREE.Object3D;
    update: (frame: AudioFrame) => void;
    dispose: () => void;
}

export interface VisualizerPreset {
    id: string;
    name: string;
    description: string;
    create: () => VisualizerScene;
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
    {id: 'halo', name: 'Spectrum halo', description: 'A rotating crown of frequency and color.', create: createHalo},
    {id: 'terrain', name: 'Wave terrain', description: 'A wireframe landscape shaped by sound.', create: createTerrain},
    {id: 'orbit', name: 'Particle orbit', description: 'An expanding constellation of sound.', create: createOrbit},
];
