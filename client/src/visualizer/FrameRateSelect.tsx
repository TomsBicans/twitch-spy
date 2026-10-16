export type FrameRate = '30' | '60' | '120' | 'native';

interface Props {
    value: FrameRate;
    onChange: (value: FrameRate) => void;
    className?: string;
}

export default function FrameRateSelect({value, onChange, className}: Props) {
    return <select className={className} aria-label="Visualizer frame rate" value={value}
        title="Frame rate limit; Native follows your display. Higher rates use more GPU."
        onChange={event => onChange(event.target.value as FrameRate)}>
        <option value="30">30 FPS</option>
        <option value="60">60 FPS</option>
        <option value="120">120 FPS</option>
        <option value="native">Native</option>
    </select>;
}
