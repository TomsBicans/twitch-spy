export function isVisualizerShortcut(event: KeyboardEvent, key: string): boolean {
    return event.key.toLowerCase() === key
        && !event.defaultPrevented && !event.repeat && !event.isComposing
        && !event.ctrlKey && !event.metaKey && !event.altKey
        && !(event.target instanceof HTMLElement
            && (event.target.isContentEditable || event.target.closest('input, select, textarea')));
}
