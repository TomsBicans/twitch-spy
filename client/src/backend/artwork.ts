import {BACKEND_URL} from "./backend";
import type {Atom} from "./models";

export function getArtworkUrl(entry: Atom | undefined): string | undefined {
    if (entry?.thumbnail_image_in_base64) return `data:image/jpeg;base64,${entry.thumbnail_image_in_base64}`;
    return entry?.thumbnail_url ? `${BACKEND_URL}${entry.thumbnail_url}` : undefined;
}
