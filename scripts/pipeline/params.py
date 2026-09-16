# 路径配置
VIDEOS_FOLDER = "Videos"  # 《罗布奥特曼》视频的文件夹
FEATURES_FILE = "face_features_insightface.npz"  # 人脸特征向量文件（爱染诚）
FRAMES_OUTPUT = "output_frames"  # 帧文件夹
SUBTITLE_OUTPUT = "subtitle_raw"  # 管线输出文件夹（权威库是 subtitle/，别指向它）
FACE_IMAGES_FOLDER = "target"  # 爱染诚人脸图片文件夹

# GPU配置
USE_GPU_FACE = True  # 人脸检测走 GPU（RTX 2050 CUDA EP 已验证）；相似度计算已改为 numpy，无需 torch
USE_GPU_OCR = False   # 是否在OCR中使用GPU
GPU_MEMORY_OCR = 500  # OCR的GPU内存限制(MB)

# OCR模型配置
OCR_MODEL_DIR = "ch_PP-OCRv4_rec_infer"  # OCR模型目录

# 字幕裁剪与分辨率配置（复刻适配点）
# 原项目针对《这就是中国》底部硬字幕条：(左, 上, 右, 下) = (235, 900, 1435, 990)，即 1920x1080 底部居中 1200x90 区域。
# 《罗布奥特曼》实测字幕位置：P01 600s 处"我们去追它吧 哥哥"位于 y≈910-980（白字黑描边），
# 原坐标 960-1050 完全没切到字幕（仅切到画面底部）。修正为更靠上的字幕带，并加宽。
SUBTITLE_AREA = (100, 895, 1820, 985)  # (left, top, right, bottom)，单位像素
REQUIRED_RESOLUTION = (1920, 1080)  # 非此分辨率会被跳过，下载务必选 1080p
