import whisper
import datetime
import argparse
import os
import json
from pydub import AudioSegment
def seconds_to_vtt_time(seconds):
    return datetime.timedelta(seconds=seconds)

def get_audio_duration(audio_path):
    audio = AudioSegment.from_file(audio_path)
    return audio.duration_seconds

def save_timestamps_with_gaps(transcriptions, output_dir, audio_filename, audio_duration):
    output_path = os.path.join(output_dir, audio_filename[:-4] + '_timestamps.json')
    timestamps = []
    last_end = 0
    index = 1  # Initialize the name index

    if transcriptions and transcriptions[0]['start'] > 0:
        timestamps.append({
            'name': index,
            'start': 0,
            'end': transcriptions[0]['start'],
            'lable': 'interval',
            'duration': transcriptions[0]['start']
        })
        index += 1  # Increment index

    for segment in transcriptions:
        duration = segment['end'] - segment['start']
        timestamps.append({
            'name': index,
            'start': segment['start'],
            'end': segment['end'],
            'lable': 'text',
            'duration': duration
        })
        last_end = segment['end']
        index += 1  # Increment index

    if last_end < audio_duration:
        timestamps.append({
            'name': index,
            'start': last_end,
            'end': audio_duration,
            'label': 'interval',
            'duration': audio_duration - last_end
        })
        # No need to increment index here as it's the last item

    with open(output_path, "w") as f:
        json.dump(timestamps, f, indent=4)

def generate_vtt(transcriptions, output_dir, audio_filename):
    output_path = os.path.join(output_dir, audio_filename[:-4] + '.vtt')
    with open(output_path, "w") as f:
        f.write("WEBVTT\n\n")
        for i, segment in enumerate(transcriptions):
            start_time = seconds_to_vtt_time(segment['start'])
            end_time = seconds_to_vtt_time(segment['end'])
            text = segment['text']
            f.write(f"{start_time} --> {end_time}\n")
            f.write(f"{text}\n\n")

def transcribe_audio_to_vtt(audio_path, language, output_dir, model="small"):
    model = whisper.load_model(model)
    result = model.transcribe(audio_path, language=language)
    audio_duration = get_audio_duration(audio_path)  # 获取音频总时长
    segments = [{
        'start': segment['start'],
        'end': segment['end'],
        'text': segment['text']
    } for segment in result['segments']]
    generate_vtt(segments, output_dir, os.path.basename(audio_path))
    ##获取时间戳
    save_timestamps_with_gaps(segments, output_dir, os.path.basename(audio_path), audio_duration)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Transcribe audio to VTT using Whisper.")
    parser.add_argument("audio_file", help="Path to the audio file")
    parser.add_argument("language", help="Language of the audio")
    parser.add_argument("vtt_output_dir", help="Output directory for the VTT files")
    args = parser.parse_args()

    transcribe_audio_to_vtt(args.audio_file, args.language, args.vtt_output_dir)
