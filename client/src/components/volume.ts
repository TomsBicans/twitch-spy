export const MIN_VOLUME_DB = -60;
const STORAGE_KEY = 'twitch-spy.volume';

interface VolumeSettings {
    volume: number;
    muted: boolean;
}

export function volumeToDb(volume: number): number {
    return Math.max(MIN_VOLUME_DB, 20 * Math.log10(volume));
}

export function dbToVolume(decibels: number): number {
    return 10 ** (Math.max(MIN_VOLUME_DB, Math.min(0, decibels)) / 20);
}

export function percentToVolume(percent: number): number {
    if (percent <= 0) return 0;
    return dbToVolume(MIN_VOLUME_DB * (1 - (Math.min(100, percent) - 1) / 99));
}

export function volumeToPercent(volume: number): number {
    if (volume <= 0) return 0;
    return Math.round(1 + 99 * (1 - volumeToDb(volume) / MIN_VOLUME_DB));
}

export function readVolumeSettings(): VolumeSettings {
    try {
        const stored: unknown = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? 'null');
        if (stored && typeof stored === 'object' && 'volume' in stored && 'muted' in stored
            && typeof stored.volume === 'number' && Number.isFinite(stored.volume)
            && stored.volume >= 0 && stored.volume <= 1 && typeof stored.muted === 'boolean') {
            return {volume: stored.volume, muted: stored.muted};
        }
    } catch (error) {
        console.warn('Could not read saved volume settings', error);
    }
    return {volume: 1, muted: false};
}

export function saveVolumeSettings(audio: HTMLAudioElement): void {
    try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify({volume: audio.volume, muted: audio.muted}));
    } catch (error) {
        console.warn('Could not save volume settings', error);
    }
}
