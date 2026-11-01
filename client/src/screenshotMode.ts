import {createContext, useContext, useLayoutEffect, useRef, useState} from "react";
import type {Atom} from "./backend/models";
import {getArtworkUrl} from "./backend/artwork";

export const ScreenshotModeContext = createContext(false);
export const useScreenshotMode = () => useContext(ScreenshotModeContext);

export function useScreenshotController() {
    const [enabled, setEnabled] = useState(() => new URLSearchParams(location.search).get("screenshot") === "1");
    const originalLocation = useRef(location.href);
    const wasEnabled = useRef(false);

    useLayoutEffect(() => {
        const cleanLocation = () => {
            const hash = location.hash === "#diagnostics" ? "#diagnostics" : "";
            history.replaceState(history.state, "", `${location.pathname}?screenshot=1${hash}`);
        };
        if (enabled) {
            if (!wasEnabled.current) originalLocation.current = location.href;
            cleanLocation();
            window.addEventListener("popstate", cleanLocation);
        } else if (wasEnabled.current) {
            const restored = new URL(originalLocation.current);
            restored.searchParams.delete("screenshot");
            history.replaceState(history.state, "", restored);
        }
        wasEnabled.current = enabled;
        return () => window.removeEventListener("popstate", cleanLocation);
    }, [enabled]);

    return {enabled, toggle: () => setEnabled(value => !value)};
}

function sampleNumber(track: Atom): number {
    let hash = 2166136261;
    for (const character of track.url) hash = Math.imul(hash ^ character.charCodeAt(0), 16777619);
    return hash >>> 0;
}

const titles = ["Midnight Current", "Soft Horizon", "Solar Drift", "Quiet Orbit",
    "After the Rain", "Velvet Skies", "Electric Bloom", "Golden Hour",
    "Moonlit Avenue", "Open Water", "Northern Lights", "Distant Echoes"];
const palettes = [["#192550", "#8b78ff", "#f9c9be"], ["#113239", "#46bea5", "#d2f4ce"],
    ["#3e2347", "#dd81ac", "#ffdcba"], ["#32234f", "#aa81e8", "#cde8ff"],
    ["#352523", "#db8f68", "#ffe4af"], ["#142e45", "#5eadd8", "#dfedff"]];

export function displayTitle(track: Atom | undefined, masked: boolean): string | undefined {
    if (!track || !masked) return track?.content_name;
    const number = sampleNumber(track);
    return `${titles[number % titles.length]} — Studio ${String(number % 1000).padStart(3, "0")}`;
}

export function displaySource(track: Atom, masked: boolean): string {
    return masked ? `https://example.invalid/demo/${sampleNumber(track) % 1000}` : track.url;
}

export function displayArtwork(track: Atom | undefined, masked: boolean): string | undefined {
    if (!track || !masked) return getArtworkUrl(track);
    const number = sampleNumber(track);
    const [background, accent, light] = palettes[number % palettes.length];
    const rotation = number % 80 - 40;
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="960" height="960" viewBox="0 0 960 960">
        <defs><linearGradient id="g" x2="1" y2="1"><stop stop-color="${background}"/>
            <stop offset="1" stop-color="${accent}"/></linearGradient></defs>
        <rect width="960" height="960" fill="url(#g)"/>
        <g transform="rotate(${rotation} 480 480)" fill="none" stroke="${light}">
            <circle cx="480" cy="420" r="245" stroke-width="2" opacity=".35"/>
            <circle cx="480" cy="420" r="205" stroke-width="65" opacity=".75"/>
            <path d="M180 650L780 190M180 720L780 260" stroke-width="2" opacity=".5"/>
        </g><circle cx="480" cy="420" r="98" fill="${background}"/>
        <text x="74" y="104" fill="${light}" font-family="sans-serif" font-size="22" letter-spacing="8">DEMO SESSIONS</text>
        <text x="74" y="824" fill="${light}" font-family="sans-serif" font-size="46" letter-spacing="3">${titles[number % titles.length].toUpperCase()}</text>
        <text x="78" y="878" fill="${light}" font-family="sans-serif" font-size="20" letter-spacing="6">STUDIO ${String(number % 1000).padStart(3, "0")}</text>
    </svg>`;
    return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
}
