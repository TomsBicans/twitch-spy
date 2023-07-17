import librosa
import numpy as np
import os.path as path
from tqdm import tqdm


def extract_hype_moments(input_file, output_file):
    chunk_duration = 10  # Process 10 seconds of audio at a time

    desired_sr = 44100
    frame_length = 2048 * desired_sr // 22050
    hop_length = frame_length // 4

    hype_audio_chunks = []

    with open(input_file, "rb") as f:
        for chunk in librosa.stream(
            f,
            block_length=chunk_duration,
            fill_value=0,
            frame_length=frame_length,
            hop_length=hop_length,
            mono=True,
        ):
            # Compute short-time Fourier transform (STFT)
            stft = librosa.stft(chunk, n_fft=frame_length, hop_length=hop_length)

            # Compute the amplitude of the STFT
            amplitude = np.abs(stft)

            # Compute the average amplitude of the chunk
            avg_amplitude = np.mean(amplitude)

            # Set a threshold for hype moments (e.g., 1.5 times the average amplitude)
            hype_threshold = 1.5 * avg_amplitude

            # Find hype moments by comparing amplitude to the threshold
            hype_moments = amplitude > hype_threshold

            # Create a mask for the original audio signal
            mask = np.repeat(hype_moments, stft.shape[1], axis=0)

            # Apply the mask to the original audio signal
            hype_audio_chunk = chunk * mask.sum(axis=0)

            hype_audio_chunks.append(hype_audio_chunk)

    # Concatenate all hype audio chunks
    hype_audio = np.concatenate(hype_audio_chunks)

    # Save the hype moments to the output file
    librosa.output.write_wav(output_file, hype_audio, desired_sr)


if __name__ == "__main__":
    ...
    res = extract_hype_moments(
        "C:\\Users\\feagl\\Documents\\GIT_REPOS\\twitch-spy\\stream_downloads\\twitch_streams\\rawchixx_2023-03-29_14-24-05.mp3",
        "sex.wav",
    )
    print(res)
