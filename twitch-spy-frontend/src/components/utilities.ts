import { Atom } from "../backend/models";

export const generatePlaylist = (
  entry: Atom,
  queriedEntries: Atom[],
  maxPlaylistSize = 100
) => {
  const playlist = [entry];
  for (const queriedEntry of queriedEntries) {
    if (queriedEntry.content_name === entry.content_name) {
      continue;
    }
    playlist.push(queriedEntry);
  }
  return playlist.slice(0, maxPlaylistSize);
};
