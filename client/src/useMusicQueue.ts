import {useState} from "react";
import type {Atom} from "./backend/models";

export function useMusicQueue(pool: Atom[]) {
    const [currentTrack, setCurrentTrack] = useState<Atom>();
    const [autoplay, setAutoplay] = useState(false);
    const [shuffle, setShuffle] = useState(false);
    const [history, setHistory] = useState<string[]>([]);
    const [future, setFuture] = useState<string[]>([]);
    const [visited, setVisited] = useState<string[]>([]);
    const byId = new Map(pool.map((track) => [track.id, track]));
    const alternatives = pool.filter((track) => track.id !== currentTrack?.id);
    const previousHistory = history.filter((id) => byId.has(id) && id !== currentTrack?.id);
    const upcoming = future.filter((id) => byId.has(id) && id !== currentTrack?.id);

    const selectTrack = (track: Atom) => {
        setCurrentTrack(track);
        setHistory([]);
        setFuture([]);
        setVisited([track.id]);
    };

    const next = () => {
        if (!alternatives.length) return;
        let track: Atom;
        if (shuffle && upcoming.length) {
            track = byId.get(upcoming[0])!;
            setFuture(upcoming.slice(1));
        } else if (shuffle) {
            const unplayed = alternatives.filter((candidate) => !visited.includes(candidate.id));
            const candidates = unplayed.length ? unplayed : alternatives;
            track = candidates[Math.floor(Math.random() * candidates.length)];
            setVisited(unplayed.length ? [...visited, track.id] : [currentTrack!.id, track.id]);
        } else {
            const index = pool.findIndex((candidate) => candidate.id === currentTrack?.id);
            track = pool[(index + 1) % pool.length];
        }
        setHistory(currentTrack ? [...history, currentTrack.id].slice(-200) : history);
        setCurrentTrack(track);
    };

    const previous = () => {
        if (shuffle) {
            const id = previousHistory.at(-1);
            if (!id) return;
            setHistory(previousHistory.slice(0, -1));
            setFuture(currentTrack ? [currentTrack.id, ...upcoming] : upcoming);
            setCurrentTrack(byId.get(id));
        } else if (alternatives.length) {
            const index = pool.findIndex((track) => track.id === currentTrack?.id);
            setCurrentTrack(pool[index <= 0 ? pool.length - 1 : index - 1]);
        }
    };

    const toggleShuffle = () => {
        setShuffle(!shuffle);
        setHistory([]);
        setFuture([]);
        setVisited(currentTrack ? [currentTrack.id] : []);
    };

    return {
        currentTrack, selectTrack, autoplay, setAutoplay, shuffle, toggleShuffle, next, previous,
        canNext: alternatives.length > 0,
        canPrevious: shuffle ? previousHistory.length > 0 : alternatives.length > 0,
    };
}
