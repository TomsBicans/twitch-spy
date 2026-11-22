import {ArrowRightToLine, Repeat, Repeat1} from "lucide-react";
import {REPEAT_LABELS, type RepeatMode} from "../playbackState";

const icons = {off: ArrowRightToLine, queue: Repeat, track: Repeat1};

interface Props {
    mode: RepeatMode;
    onCycle: () => void;
}

export default function RepeatButton({mode, onCycle}: Props) {
    const Icon = icons[mode];
    const label = REPEAT_LABELS[mode];
    return <button type="button" onClick={onCycle} data-repeat-active={mode !== "off"}
        aria-label={label} title={`${label} · Change repeat mode`}>
        <Icon size={16} aria-hidden="true"/>
    </button>;
}
