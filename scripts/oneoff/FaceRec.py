import dlib
import cv2
import numpy as np
import os
from sklearn.metrics.pairwise import cosine_similarity


class FaceRecognizer:
    def __init__(self, features_file):
        # 加载dlib模型
        self.detector = dlib.get_frontal_face_detector()
        self.shape_predictor = dlib.shape_predictor("dlib_module/shape_predictor_68_face_landmarks.dat")
        self.face_rec_model = dlib.face_recognition_model_v1("dlib_module/dlib_face_recognition_resnet_model_v1.dat")

        # 加载预计算的特征向量
        self.load_features(features_file)

    def load_features(self, features_file):
        """从NPZ文件加载预计算的特征向量"""
        print(f"Loading pre-computed features from {features_file}")
        data = np.load(features_file)
        self.known_face_encodings = data['encodings']
        self.image_paths = data['image_paths']
        print(f"Loaded {len(self.known_face_encodings)} face features")

    def extract_face_encodings(self, image):
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        faces = self.detector(rgb_image)

        face_encodings = []
        for face in faces:
            shape = self.shape_predictor(rgb_image, face)
            face_encoding = np.array(self.face_rec_model.compute_face_descriptor(rgb_image, shape))
            face_encodings.append(face_encoding)

        return face_encodings

    def recognize_face(self, frame, threshold=0.6):
        face_encoding = self.extract_face_encoding(frame)

        if face_encoding is None:
            return False

        # 计算与所有已知人脸的相似度
        similarities = [cosine_similarity(face_encoding.reshape(1, -1),
                                          known_encoding.reshape(1, -1))[0][0]
                        for known_encoding in self.known_face_encodings]

        if not similarities:
            return False

        max_similarity = max(similarities)
        return max_similarity > threshold

    def get_face_similarity(self, frame):
        face_encodings = self.extract_face_encodings(frame)
        if not face_encodings:  # 如果没有检测到人脸
            return None

        # 确保known_face_encodings不为空
        if len(self.known_face_encodings) == 0:
            return None

        # 将已知特征向量转换为NumPy数组
        known_encodings = np.array(self.known_face_encodings)

        max_similarity = 0
        for face_encoding in face_encodings:
            # 计算余弦相似度
            similarities = cosine_similarity(known_encodings, face_encoding.reshape(1, -1))
            max_similarity = max(max_similarity, np.max(similarities))

        return max_similarity if max_similarity > 0 else None

    def process_video(self, video_path, fps=1, save_frames_folder="output_frames"):
        """处理视频，检测所有人脸，保存所有帧和相似度"""
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print("Error: Cannot open video file.")
            return

        if not os.path.exists(save_frames_folder):
            os.makedirs(save_frames_folder)

        frame_rate = cap.get(cv2.CAP_PROP_FPS)
        interval = int(frame_rate / fps)
        frame_count = 0
        video_title = os.path.splitext(os.path.basename(video_path))[0]

        print("Processing video...")
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            if frame_count % interval == 0:
                time_sec = frame_count / frame_rate
                minutes = int(time_sec // 60)
                seconds = int(time_sec % 60)
                similarity = self.get_face_similarity(frame)

                # 为没有检测到人脸的帧设置相似度为0
                similarity = similarity if similarity is not None else 0.0
                
                # 保存每一帧及其相似度
                frame_filename = os.path.join(
                    save_frames_folder,
                    f"{video_title}_{minutes}m{seconds:02d}s_sim_{similarity:.3f}.jpg"
                )
                cv2.imwrite(frame_filename, frame)
                print(f"Frame {frame_count}: {minutes}m{seconds:02d}s - similarity = {similarity:.3f}")

            frame_count += 1

        cap.release()
        print(f"All frames saved to {save_frames_folder}")

    def process_video_with_params(self, video_path, output_folder, fps=1):
        """修改后的视频处理方法，不再需要target_folder参数"""
        self.process_video(video_path, fps, output_folder)