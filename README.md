# EchoAccess

结合主流技术，实现无障碍字幕自动化功能的实验探索

## 实验环境

- Windows 11
- Python 3.8.3

## 自动化字幕生成功能实现



![echoaccess](./img/echoacess.png)

### 技术路线

- 音频分类模型：PSLA框架

- 多模态说话人识别：3D-Speaker，一个结合CAM++和TalkNet的多模态说话人分割聚类处理流程

  ![3d-speaker](./img/3d-speaker.jpg)

- 语音识别模型：Whisper模型

### 数据集

- MSDWild数据集：一个用于多模态说话人分割聚类任务的数据集
