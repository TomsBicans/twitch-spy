import {useEffect, useMemo, useState} from "react";
import type {Atom} from "./backend/models";
import {readPlaybackState, writePlaybackState, type LibraryFilter, type RepeatMode} from "./playbackState";

const NEXT_REPEAT_MODE: Record<RepeatMode, RepeatMode> = {off: "queue", queue: "track", track: "off"};

export interface QueueEntry {
    track: Atom;
    position: number;
}

function shuffled(tracks: Atom[], seed: number): Atom[] {
    const result = [...tracks].sort((a, b) => a.url < b.url ? -1 : a.url > b.url ? 1 : 0);
    let random = seed;
    for (let index = result.length - 1; index > 0; index--) {
        random = (Math.imul(random, 1664525) + 1013904223) >>> 0;
        const other = Math.floor((random / 4294967296) * (index + 1));
        [result[index], result[other]] = [result[other], result[index]];
    }
    return result;
}

export function useMusicQueue(pool: Atom[], library: Atom[], ready: boolean, screenshotMode = false) {
    const [state, setState] = useState(readPlaybackState);
    const currentTrack = library.find(track => track.url === state.track);
    const anchor = library.find(track => track.url === state.anchor);
    const order = useMemo(() => {
        if (!state.shuffle) return pool;
        const rest = shuffled(pool.filter(track => track.url !== state.anchor), state.seed);
        return pool.some(track => track.url === state.anchor) && anchor ? [anchor, ...rest] : rest;
    }, [pool, state.shuffle, state.seed, state.anchor, anchor]);

    useEffect(() => {
        if (!screenshotMode) writePlaybackState(state);
    }, [state, screenshotMode]);

    useEffect(() => {
        const restore = () => { if (!screenshotMode) setState(readPlaybackState()); };
        window.addEventListener("popstate", restore);
        return () => window.removeEventListener("popstate", restore);
    }, [screenshotMode]);

    const anchorIndex = order.findIndex(track => track.url === state.anchor);
    const indexAt = (position: number): number => {
        const offset = anchorIndex >= 0 ? anchorIndex + position : position > 0 ? position - 1 : position;
        return ((offset % order.length) + order.length) % order.length;
    };
    const trackAt = (position: number): Atom | undefined => {
        if (position === 0 && anchor) return anchor;
        if (!order.length) return undefined;
        return order[indexAt(position)];
    };
    const currentInOrder = order.some(track => track.url === state.track);
    const canNext = ready && order.some(track => track.url !== state.track);
    const canPrevious = canNext && (!state.shuffle || state.position > state.start);
    const upcomingPosition = (offset: number): number => {
        const position = state.position + offset;
        // Keep a filtered-out anchor in history without replaying it automatically.
        return anchorIndex < 0 && state.position < 0 && position >= 0 ? position + 1 : position;
    };
    const nextIndex = order.length ? indexAt(upcomingPosition(1)) : 0;
    const remaining = currentInOrder && nextIndex === 0 ? 0 : order.length - nextIndex;
    const repeatQueue = state.repeat === "queue";
    const autoplay = state.autoplay || repeatQueue;
    const loopCurrentTrack = state.repeat === "track" || (repeatQueue && ready && currentInOrder && !canNext);
    const canAutoAdvance = autoplay && !loopCurrentTrack && canNext && (repeatQueue || remaining > 0);
    const jumpTo = (position: number) => {
        const track = trackAt(position);
        if (!track || !Number.isSafeInteger(position)) return;
        setState(previous => ({...previous, track: track.url, position, start: Math.min(previous.start, position)}));
    };
    const selectTrack = (track: Atom) => setState(previous => ({
        ...previous, track: track.url, anchor: track.url, position: 0, start: 0,
    }));
    const setFilter = (filter: LibraryFilter) => setState(previous => ({
        ...previous, ...filter, anchor: previous.track, position: 0, start: 0,
    }));
    const history: QueueEntry[] = [];
    const upcoming: QueueEntry[] = [];
    if (ready && currentTrack) {
        for (let position = Math.max(state.start, state.position - 200); position < state.position; position++) {
            const track = trackAt(position);
            if (track) history.push({track, position});
        }
        if (canNext) {
            const count = repeatQueue ? order.length - Number(currentInOrder) : remaining;
            for (let offset = 1; offset <= count; offset++) {
                const position = upcomingPosition(offset);
                const track = trackAt(position);
                if (track) upcoming.push({track, position});
            }
        }
    }

    return {
        currentTrack, selectTrack, history, upcoming, jumpTo, canNext, canPrevious,
        position: state.position, autoplay, loopCurrentTrack,
        onTrackEnded: () => { if (canAutoAdvance) jumpTo(upcomingPosition(1)); },
        toggleAutoplay: () => setState(previous => previous.repeat === "queue"
            ? {...previous, autoplay: false, repeat: "off"}
            : {...previous, autoplay: !previous.autoplay}),
        repeatMode: state.repeat,
        cycleRepeatMode: () => setState(previous => ({...previous, repeat: NEXT_REPEAT_MODE[previous.repeat]})),
        shuffle: state.shuffle,
        toggleShuffle: () => setState(previous => ({
            ...previous, shuffle: !previous.shuffle, anchor: previous.track, position: 0, start: 0,
        })),
        filter: {search: state.search, status: state.status}, setFilter,
        next: () => {
            if (!canNext) return;
            if (!currentTrack) selectTrack(pool[0]);
            else jumpTo(state.position + 1);
        },
        previous: () => {
            if (!canPrevious) return;
            if (!currentTrack) selectTrack(pool[pool.length - 1]);
            else jumpTo(state.position - 1);
        },
    };
}
