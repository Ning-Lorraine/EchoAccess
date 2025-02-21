import os
import torch
import torchaudio
import argparse
from collections import OrderedDict
import soundfile as sf
import models
import torch.nn.functional as F
import csv
import json

def load_label_index(label_csv):
    index_lookup = {}
    with open(label_csv, 'r') as f:
        csv_reader = csv.DictReader(f)
        for row in csv_reader:
            index_lookup[int(row['index'])] = row['display_name']
    return index_lookup

class Relay:
    def __init__(self, audio_conf):
        self.audio_conf = audio_conf
        self.melbins = audio_conf.get('num_mel_bins')
        self.target_length = audio_conf.get('target_length')
        self.norm_mean = audio_conf.get('mean')
        self.norm_std = audio_conf.get('std')

    def _wav2fbank(self, waveform, sr):
        waveform = waveform - waveform.mean()
        fbank = torchaudio.compliance.kaldi.fbank(waveform, htk_compat=True, sample_frequency=sr, use_energy=False,
                                                  window_type='hanning', num_mel_bins=self.melbins, dither=0.0,
                                                  frame_shift=10)
        n_frames = fbank.shape[0]
        p = self.target_length - n_frames
        if p > 0:
            fbank = torch.nn.functional.pad(fbank, (0, 0, 0, p))
        elif p < 0:
            fbank = fbank[:self.target_length, :]
        return fbank

    def preprocess(self, data, sr):
        fbank = self._wav2fbank(data, sr)
        fbank = (fbank - self.norm_mean) / self.norm_std
        return fbank.unsqueeze(0)

# def predict_and_save(audio_dir, model, relay, labels_index, output_json):
#     results = {}
#     threshold = 0.0056  # 设置概率阈值为0.56
#     for root, _, files in os.walk(audio_dir):
#         for file in files:
#             if file.lower().endswith('.wav'):
#                 file_path = os.path.join(root, file)
#                 waveform, sample_rate = torchaudio.load(file_path)
#                 data = relay.preprocess(waveform, sample_rate)
#                 outputs = model(data.cuda())
#                 probabilities = F.softmax(outputs, dim=1)
#                 # 筛选出概率大于0.56的类别及其概率
#                 selected_probs, selected_indices = torch.where(probabilities > threshold, probabilities, torch.tensor(0.0).cuda()), torch.where(probabilities > threshold, torch.arange(probabilities.size(1)).cuda(), torch.tensor(-1).cuda())
#                 selected_probs = selected_probs[selected_probs != 0]
#                 selected_indices = selected_indices[selected_indices != -1]
#                 # 保存筛选后的结果
#                 results[file[:-4]] = [(labels_index[idx.item()], prob.item()) for idx, prob in zip(selected_indices[0], selected_probs[0]) if prob > 0]

#     with open(output_json, 'w') as f:
#         json.dump(results, f, indent=4)
# def predict_and_save(audio_dir, model, relay, labels_index, output_json):
#     results = {}
#     threshold = 0.0056  # 设置概率阈值为0.56
#     for root, _, files in os.walk(audio_dir):
#         for file in files:
#             if file.lower().endswith('.wav'):
#                 file_path = os.path.join(root, file)
#                 waveform, sample_rate = torchaudio.load(file_path)
#                 data = relay.preprocess(waveform, sample_rate)
#                 outputs = model(data.cuda())
#                 probabilities = F.softmax(outputs, dim=1)
#                 # 筛选出概率大于0.56的类别及其概率
#                 mask = probabilities > threshold
#                 selected_probs = probabilities[mask]
#                 selected_indices = torch.arange(probabilities.size(1))[mask]
                
#                 # 检查selected_indices是否为空
#                 if selected_indices.nelement() == 0:
#                     print(f"No predictions above threshold for {file}")
#                     results[file[:-4]] = []
#                 else:
#                     # 保存筛选后的结果
#                     results[file[:-4]] = [(labels_index[idx.item()], prob.item()) for idx, prob in zip(selected_indices, selected_probs)]

#     with open(output_json, 'w') as f:
#         json.dump(results, f, indent=4)
##原来
# def predict_and_save(audio_dir, model, relay, labels_index, output_json):
#     results = {}
#     for root, _, files in os.walk(audio_dir):
#         for file in files:
#             if file.lower().endswith('.wav'):
#                 file_path = os.path.join(root, file)
#                 print(file_path)
#                 waveform, sample_rate = torchaudio.load(file_path)
#                 data = relay.preprocess(waveform, sample_rate)
#                 outputs = model(data.cuda())
#                 probabilities = F.softmax(outputs, dim=1)
#                 topk_probs, topk_indices = torch.topk(probabilities, 10)
#                 print('输出值和标签',topk_probs)  # 输出值和标签
#                 results[file[:-4]] = [labels_index[idx.item()] for idx in topk_indices[0]]
#                 print('类别：',results[file[:-4]])

#     with open(output_json, 'w') as f:
#         json.dump(results, f, indent=4)
#######
def predict_and_update(audio_dir, model, relay, labels_index, output_json):
    with open(output_json, 'r') as f:
        timestamps = json.load(f)
    threshold = 0.0056  # 设置概率阈值为0.56
    # Map the name to the classification result
    for entry in timestamps:
        file_name = f"{entry['name']}.wav"
        file_path = os.path.join(audio_dir, file_name)
        if os.path.exists(file_path):
            waveform, sample_rate = torchaudio.load(file_path)
            data = relay.preprocess(waveform, sample_rate)
            outputs = model(data.cuda())
            probabilities = F.softmax(outputs, dim=1)
                            # 确保概率张量是二维的
            if probabilities.dim() == 1:
                probabilities = probabilities.unsqueeze(0)
            
            # 创建索引数组，并确保它在正确的设备上
            device = probabilities.device  # 获取概率张量所在的设备
            indices = torch.arange(probabilities.size(1), device=device)  # 在相同的设备上创建索引数组

            # 使用掩码选择超过阈值的概率
            mask = probabilities > threshold
            selected_probs = probabilities[mask]
            selected_indices = indices[mask.squeeze()]  # 应用掩码并确保掩码是一维的

            # 如果没有任何概率超过阈值
            if selected_indices.nelement() == 0:
                max_prob, max_index = torch.max(probabilities, dim=1)
                max_class = labels_index[max_index.item()]
                mclass = []
                mclass.append(max_class)
                entry['class']=mclass
                # results[file[:-4]] = [(max_class, max_prob.item())]
                # print(f"No predictions above threshold for {file}")
                # print(f"No predictions above threshold for {file}")
            else:
                # 提取类别和对应的概率
                class_prob_pairs = [(labels_index[idx.item()]) for idx in selected_indices]
                # 过滤掉“Human_voice”标签
                filtered_pairs = [pair for pair in class_prob_pairs if pair != 'Human_voice']
                if not filtered_pairs:
                    max_prob, max_index = torch.max(probabilities, dim=1)
                    max_class = labels_index[max_index.item()]
                    mclass = []
                    mclass.append(max_class)
                    entry['class']=mclass
                else:
                    # 根据概率值对结果进行排序，概率高的排在前面
                    sorted_pairs = sorted(filtered_pairs, key=lambda x: x[1], reverse=True)
                    # print(sorted_pairs)
                    # result_pairs = [labels_index[idx] for idx in sorted_pairs]
                    entry['class'] = sorted_pairs
                # print(sorted_pairs)
                # results[file[:-4]] = sorted_pairs
            
            # entry['class'] = labels_index[top_index.item()]

    # Write the updated timestamp data back to the JSON file or to a new file
    with open(output_json, 'w') as f:
        json.dump(timestamps, f, indent=4)
        

def main(audio_dir, label_csv, model_path, output_json):
    # Load model and label index
    model = models.EffNetAttention(label_dim=200, b=2, pretrain=True, head_num=4)
    model = torch.nn.DataParallel(model)
    model.load_state_dict(torch.load(model_path))
    model.eval().cuda()

    labels_index = load_label_index(label_csv)

    audio_conf = {'num_mel_bins': 128, 'target_length': 100, 'mean': -4.6476, 'std': 4.5699}
    relay = Relay(audio_conf)

    predict_and_update(audio_dir, model, relay, labels_index, output_json)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--audio_dir", type=str, default='./example/result/7speakers_example', help="Directory containing audio files")
    parser.add_argument("--label_csv", type=str, default='./labels/class_labels.csv', help="CSV file with label indexes and display names")
    parser.add_argument("--model_path", type=str, default="./models/best_audio_model.pth", help="Path to the trained model")
    parser.add_argument("--output_json", type=str, default="1.json", help="Path to save the output JSON file")
    args = parser.parse_args()

    main(args.audio_dir, args.label_csv, args.model_path, args.output_json)
