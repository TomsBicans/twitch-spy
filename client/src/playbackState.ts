import {ProcessingStates} from "./backend/models";

export interface LibraryFilter {
    search: string;
    status: ProcessingStates | "all";
}

interface PlaybackState extends LibraryFilter {
    autoplay: boolean;
    shuffle: boolean;
    seed: number;
    anchor: string;
    track: string;
    position: number;
    start: number;
}

function integer(value: string | null, fallback: number): number {
    if (value === null || value.trim() === "") return fallback;
    const parsed = Number(value);
    return Number.isSafeInteger(parsed) && Math.abs(parsed) <= 1_000_000_000 ? parsed : fallback;
}

export function readPlaybackState(): PlaybackState {
    const params = new URLSearchParams(window.location.search);
    const status = params.get("status");
    const position = integer(params.get("position"), 0);
    const track = params.get("track") ?? "";
    return {
        autoplay: params.get("autoplay") === "1",
        shuffle: params.get("shuffle") === "1",
        seed: integer(params.get("seed"), 1 + crypto.getRandomValues(new Uint32Array(1))[0] % 999_999_999),
        anchor: params.get("anchor") ?? track,
        track, position,
        start: Math.min(integer(params.get("from"), 0), position),
        search: params.get("q") ?? "",
        status: status === "all" || Object.values(ProcessingStates).includes(status as ProcessingStates)
            ? status as LibraryFilter["status"] : ProcessingStates.FINISHED,
    };
}

export function writePlaybackState(state: PlaybackState): void {
    const url = new URL(window.location.href);
    const values = {
        autoplay: state.autoplay ? "1" : "0", shuffle: state.shuffle ? "1" : "0",
        seed: String(state.seed), track: state.track, anchor: state.anchor,
        position: state.track ? String(state.position) : "",
        from: state.start ? String(state.start) : "", q: state.search,
        status: state.status === ProcessingStates.FINISHED ? "" : state.status,
    };
    for (const [key, value] of Object.entries(values)) {
        if (value) url.searchParams.set(key, value);
        else url.searchParams.delete(key);
    }
    if (url.href !== window.location.href) window.history.replaceState(window.history.state, "", url);
}
