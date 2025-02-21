import json
import os
import sys
from pydub import AudioSegment

def split_audio(json_path, audio_path, base_output_dir):
    # Load the audio file
    audio = AudioSegment.from_file(audio_path)

    # Load timestamps from the JSON file
    with open(json_path, 'r') as f:
        timestamps = json.load(f)

    # Get the base name of the audio file and create a specific output directory
    audio_basename = os.path.splitext(os.path.basename(audio_path))[0]
    output_dir = os.path.join(base_output_dir, audio_basename)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Process each timestamp and split the audio
    for item in timestamps:
        start_ms = int(item['start'] * 1000)  # Convert seconds to milliseconds
        end_ms = int(item['end'] * 1000)
        audio_segment = audio[start_ms:end_ms]
        segment_filename = f"{item['name']}.wav"
        segment_path = os.path.join(output_dir, segment_filename)
        audio_segment.export(segment_path, format="wav")
        # print(f"Exported {segment_path}")
    print("Clip wav to segments.")

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python split_audio.py <json_path> <audio_path> <base_output_dir>")
        sys.exit(1)

    json_path = sys.argv[1]
    audio_path = sys.argv[2]
    base_output_dir = sys.argv[3]

    split_audio(json_path, audio_path, base_output_dir)
