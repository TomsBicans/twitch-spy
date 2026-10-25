import {useEffect, useId, useRef, useState} from 'react';
import {SlidersHorizontal, Volume2, VolumeX, X} from 'lucide-react';
import {dbToVolume, MIN_VOLUME_DB, percentToVolume, volumeToDb, volumeToPercent} from './volume';
import styles from './VolumeControl.module.css';

export default function VolumeControl({audio}: {audio: HTMLAudioElement}) {
    const [playback, setPlayback] = useState({volume: audio.volume, muted: audio.muted});
    const [settingsOpen, setSettingsOpen] = useState(false);
    const settingsId = useId();
    const settingsButton = useRef<HTMLButtonElement>(null);
    const settingsPanel = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (!settingsOpen) return;
        settingsPanel.current?.querySelector('input')?.focus();
        const dismiss = (event: PointerEvent) => {
            if (event.target instanceof Node && !settingsPanel.current?.contains(event.target)
                && !settingsButton.current?.contains(event.target)) setSettingsOpen(false);
        };
        document.addEventListener('pointerdown', dismiss);
        return () => document.removeEventListener('pointerdown', dismiss);
    }, [settingsOpen]);

    useEffect(() => {
        const sync = () => setPlayback({volume: audio.volume, muted: audio.muted});
        sync();
        audio.addEventListener('volumechange', sync);
        return () => audio.removeEventListener('volumechange', sync);
    }, [audio]);

    const decibels = Math.round(volumeToDb(playback.volume));
    const silent = playback.muted || playback.volume === 0;
    const percent = silent ? 0 : volumeToPercent(playback.volume);
    const closeSettings = () => {
        setSettingsOpen(false);
        settingsButton.current?.focus();
    };
    const setVolume = (value: number) => {
        if (!Number.isFinite(value)) return;
        audio.volume = dbToVolume(value);
        audio.muted = false;
    };

    return <div className={styles.control} role="group" aria-label="Playback volume"
        onKeyDown={event => {
            event.stopPropagation();
            if (event.key === 'Escape' && settingsOpen) {
                event.preventDefault();
                closeSettings();
            }
        }}>
        <button type="button" className={styles.iconButton} aria-label={silent ? 'Unmute' : 'Mute'}
            title={silent ? 'Unmute' : 'Mute'} onClick={() => {
                if (audio.volume === 0) audio.volume = dbToVolume(MIN_VOLUME_DB);
                audio.muted = !silent;
            }}>
            {silent ? <VolumeX size={18}/> : <Volume2 size={18}/>}
        </button>
        <div className={styles.sliderWrap}>
            <output className={styles.percentage} aria-hidden="true">{percent}%</output>
            <input className={styles.slider} aria-label="Volume" aria-valuetext={silent ? 'Muted' : `${percent}%`}
                type="range" min="0" max="100" step="1" value={percent}
                onChange={event => {
                    const value = Number(event.target.value);
                    if (value === 0) audio.muted = true;
                    else {
                        audio.volume = percentToVolume(value);
                        audio.muted = false;
                    }
                }}/>
        </div>
        <button ref={settingsButton} type="button" className={styles.iconButton} aria-label="Audio settings"
            title="Audio settings" aria-expanded={settingsOpen} aria-controls={settingsOpen ? settingsId : undefined}
            aria-haspopup="dialog" onClick={() => setSettingsOpen(value => !value)}>
            <SlidersHorizontal size={16}/>
        </button>
        {settingsOpen && <div ref={settingsPanel} id={settingsId} className={styles.settings}
            role="dialog" aria-label="Audio settings" onBlur={event => {
                if (!event.currentTarget.contains(event.relatedTarget)
                    && event.relatedTarget !== settingsButton.current) setSettingsOpen(false);
            }}>
            <div className={styles.heading}>
                <h3>Audio settings</h3>
                <button type="button" className={styles.iconButton} aria-label="Close audio settings"
                    onClick={closeSettings}><X size={16}/></button>
            </div>
            <form onSubmit={event => {
                event.preventDefault();
                const value = new FormData(event.currentTarget).get('volumeDb');
                if (typeof value !== 'string' || !value.trim()) return;
                setVolume(Number(value));
                closeSettings();
            }}>
                <label className={styles.level}>
                    <span>Precise volume</span>
                    <input aria-label="Volume in decibels" name="volumeDb" type="number"
                        min={MIN_VOLUME_DB} max="0" step="1" defaultValue={decibels} required/>
                    <span>dB</span>
                </label>
                <button className={styles.apply} type="submit">Apply</button>
            </form>
            <p>0 dB is the original level. Negative values are quieter.</p>
        </div>}
    </div>;
}
