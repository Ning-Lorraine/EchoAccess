## 将rttm和asr生成的vtt格式文件结合起来
import re
import argparse
import json

def parse_timecode(time_str):
    h, m, s = map(float, time_str.replace(',', '.').split(':'))
    return round(3600 * h + 60 * m + s, 3)

def parse_rttm(rttm_file):
    speakers = []
    with open(rttm_file, 'r') as f:
        lines = f.readlines()
        for line in lines:
            parts = line.split()
            start_time = float(parts[3])  # Assuming start time is in the fourth column
            duration = float(parts[4])  # Assuming duration is in the fifth column
            end_time = round(start_time + duration, 3)  # Calculate end time and round to three decimal places
            speaker_info = {
                'speaker': parts[7],  # Assuming speaker info is in the second column
                'start': round(start_time, 3),  # Round start time to three decimal places
                'end': end_time,
                'duration': round(duration, 3)  # Round duration to three decimal places
            }
            speakers.append(speaker_info)
    # print(speakers)
    return speakers

# 解析vtt文件
def parse_vtt(vtt_file):
    subtitles = []

    with open(vtt_file, 'r') as f:
        lines = f.readlines()
        subtitle = {}
        skip_first_line = True
        for line in lines:
            line = line.strip()
            if skip_first_line:
                skip_first_line = False
                continue
            if '-->' in line:
                times = line.split('-->')
                subtitle['start'] = parse_timecode(times[0])
                subtitle['end'] = parse_timecode(times[1])
            elif line:
                subtitle['text'] = line.lstrip()
                subtitles.append(subtitle)
                subtitle = {}
    # print(subtitles)
    return subtitles

def parse_classification(json_file):
    with open(json_file, 'r') as file:
        data = json.load(file)
    return data

def format_classification(classes):
    return ' '.join(f"[ {cls.lower()} ]" for cls in classes)

def format_time(seconds):
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{int(hours):02d}:{int(minutes):02d}:{seconds:06.3f}"

### 原函数
# def merge_rttm_to_vtt(vtt_file, rttm_file):
#     subtitles = parse_vtt(vtt_file)
#     # print(subtitles)
#     speakers = parse_rttm(rttm_file)
#     merged_subtitles = []

#     for subtitle in subtitles:
#         subtitle_text = subtitle['text']
#         start_time = subtitle['start']
#         end_time = subtitle['end']
#         speaker_label = None

#         for speaker in speakers:
#             speaker_start = speaker['start']
#             speaker_end = speaker['end']  # Calculate end time from duration
#             speaker_label = speaker['speaker']

#             # Check if subtitle timestamp is within speaker segment
#             if (speaker_start <= start_time and speaker_end >= end_time) or \
#                     (abs(speaker_start - start_time)<0.5 and speaker_end >= end_time) or \
#                     (speaker_start <= start_time and abs(speaker_end - end_time) < 1.0) or \
#                     (abs(speaker_start - start_time)<0.5 and abs(speaker_end - end_time) < 1.0)  :
#                 break

#         # Add speaker label to subtitle text
#         if speaker_label:
#             subtitle_text = f"<v Speaker{speaker_label}> {subtitle_text}"

#         merged_subtitles.append({
#             'start': format_time(start_time),
#             'end': format_time(end_time),
#             'text': subtitle_text
#         })

#     return merged_subtitles

def merge_rttm_to_vtt(vtt_file, rttm_file, class_json_file):
    subtitles = parse_vtt(vtt_file)
    speakers = parse_rttm(rttm_file)
    classifications = parse_classification(class_json_file)
    merged_subtitles = []

    for subtitle in subtitles:
        start_time = subtitle['start']
        end_time = subtitle['end']
        subtitle_text = subtitle['text']

        # 查找对应时间内的分类
        classification_text = ""
        for classification in classifications:
            # print('start_time:',classification['start'],' end:',classification['end'])
            if abs(classification['start'] - start_time)<0.1 and abs(classification['end'] - end_time)<0.1:
                classification_text = format_classification(classification['class'])
                break

        # 组合说话人和分类信息
        speaker_label = next((s['speaker'] for s in speakers if s['start'] <= start_time < s['end']), None)
        if speaker_label:
            formatted_text = f"{classification_text}\n<v Speaker{speaker_label}> {subtitle_text}"
        else:
            formatted_text = f"{classification_text}\n {subtitle_text}"

        merged_subtitles.append({
            'start': format_time(start_time),
            'end': format_time(end_time),
            'text': formatted_text
        })

    return merged_subtitles

def write_merged_vtt(subtitles, output_file):
    with open(output_file, 'w') as f:
        f.write('WEBVTT\n')
        f.write('kind: captions\n\n')
        for subtitle in subtitles:
            f.write(f"{subtitle['start']} --> {subtitle['end']}\n")
            f.write(f"{subtitle['text']}\n\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Merge VTT and RTTM files.")
    parser.add_argument("vtt_file", help="Path to the VTT file")
    parser.add_argument("rttm_file", help="Path to the RTTM file")
    parser.add_argument("output_file", help="Path for the output merged VTT file")
    parser.add_argument("class_json_file", help="Path for the audio tagging file")
    args = parser.parse_args()

    subtitles = merge_rttm_to_vtt(args.vtt_file, args.rttm_file, args.class_json_file)
    write_merged_vtt(subtitles, args.output_file)