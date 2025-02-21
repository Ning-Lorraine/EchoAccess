#!/bin/bash

set -e
. ./path.sh || exit 1

stage=1
stop_stage=7

video_list=examples/video.list
exp=exp_video
conf_file=conf/diar_video.yaml
onnx_dir=pretrained_models
gpus="0"
nj=4
language="English"   # 设置语言参数

. local/parse_options.sh || exit 1

raw_data_dir=$exp/raw
visual_embs_dir=$exp/embs_video
rttm_dir=$exp/rttm
vtt_output_dir=$exp/result

if [ "${stage}" -le 1 ] && [ "${stop_stage}" -ge 1 ]; then
  echo "examples/test1.mp4" > examples/video.list
  echo "examples/test2.mp4" > examples/video.list
fi

if [ "${stage}" -le 2 ] && [ "${stop_stage}" -ge 2 ]; then
  mkdir -p $raw_data_dir || { echo "Error: Failed to create raw data directory $raw_data_dir"; exit 1; }

  ## 加载3D-speaker中用于speaker diarization的模型
  #  mkdir -p $onnx_dir
  # for m in version-RFB-320.onnx asd.onnx fqa.onnx face_recog_ir101.onnx; do
  #   if [ ! -e $onnx_dir/$m ]; then
  #     echo "$(basename $0) Stage2: Download pretrained models $m"
  #     wget -O $onnx_dir/$m "https://modelscope.cn/api/v1/models/iic/speech_campplus_speaker-diarization_common/repo?Revision=master&FilePath=onnx/$m"
  #   fi
  # done

  cat $video_list | while read video_file; do
    filename=$(basename $video_file)
    out_video_file=$raw_data_dir/${filename%.*}.mp4
    out_wav_file=$raw_data_dir/${filename%.*}.wav

    if [ ! -e $out_video_file ]; then
      ffmpeg -nostdin -y -i $video_file -qscale:v 2 -threads 16 -async 1 -r 25 $out_video_file -loglevel panic
    fi

    if [ ! -e $out_wav_file ]; then
      ffmpeg -nostdin -y -i $out_video_file -qscale:a 0 -ac 1 -vn -threads 16 -ar 16000 $out_wav_file -loglevel panic
    fi
  done

  # Step Whisper 转录生成文本
  for wav_file in $raw_data_dir/*.wav; do
    python3 transcribe.py "$wav_file" "$language" "$vtt_output_dir"
  done
fi

if [ "${stage}" -le 3 ] && [ "${stop_stage}" -ge 3 ]; then
  for wav_file in $raw_data_dir/*.wav; do
    base_name=$(basename "$wav_file" .wav)
    json_file="${vtt_output_dir}/${base_name}_timestamps.json"
    audio_output_dir="${vtt_output_dir}/${base_name}" 

    if [ -f "$json_file" ]; then
      # Step 音频分割
      python3 split_audio.py "$json_file" "$wav_file" "$vtt_output_dir"

      # Step 音频分类
      python audio_tagging.py \
            --audio_dir "$audio_output_dir" \
            --label_csv "./labels/class_labels.csv" \
            --model_path "./models/best_audio_model.pth" \
            --output_json "$json_file"
    else
      echo "Warning: No timestamp file found for $wav_file, skipping audio split and classification."
    fi
  done
fi

cat $video_list | while read video_file; do filename=$(basename $video_file);echo $raw_data_dir/${filename%.*}.mp4;done > $raw_data_dir/video.list
cat $video_list | while read video_file; do filename=$(basename $video_file);echo $raw_data_dir/${filename%.*}.wav;done > $raw_data_dir/wav.list

# Step 说话人分割聚类：提取音频向量
if [ ${stage} -le 4 ] && [ ${stop_stage} -ge 4 ]; then
  echo "$(basename $0) Stage3: Extract audio speaker embeddings..."
  bash run_audio.sh --stage 2 --stop_stage 4 --wav_list $raw_data_dir/wav.list --exp $exp
fi
# Step 说话人分割聚类：提取视觉向量
if [ ${stage} -le 5 ] && [ ${stop_stage} -ge 5 ]; then
  echo "$(basename $0) Stage4: Extract visual speaker embeddings..."
  torchrun --nproc_per_node=$nj local/extract_visual_embeddings.py --conf $conf_file --videos $raw_data_dir/video.list \
          --vad $exp/json/vad.json --onnx_dir $onnx_dir --embs_out $visual_embs_dir --gpu $gpus --use_gpu
fi
# Step 说话人分割聚类：聚类并生成 rttm 文件
if [ ${stage} -le 6 ] && [ ${stop_stage} -ge 6 ]; then
  echo "$(basename $0) Stage5: Clustering for both type of speaker embeddings..."
  torchrun --nproc_per_node=$nj local/cluster_and_postprocess.py --conf $conf_file --wavs $raw_data_dir/wav.list \
          --audio_embs_dir $exp/embs --visual_embs_dir $visual_embs_dir --rttm_dir $rttm_dir
fi

# Step 生成vtt文件
if [ "${stage}" -le 7 ] && [ "${stop_stage}" -ge 7 ]; then
  for wav_file in $raw_data_dir/*.wav; do
    base_name=$(basename "$wav_file" .wav)
    vtt_file="$vtt_output_dir/${base_name}.vtt"
    rttm_file="${rttm_dir}/${base_name}.rttm"
    output_vtt_file="${vtt_output_dir}/${base_name}_merged.vtt"
    class_json_file="${vtt_output_dir}/${base_name}_timestamps.json"
    python3 merge.py "$vtt_file" "$rttm_file" "$output_vtt_file" "$class_json_file"
    done
fi

echo "Process completed."
