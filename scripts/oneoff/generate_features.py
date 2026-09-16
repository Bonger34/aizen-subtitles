import dlib
import cv2
import numpy as np
import os
from tqdm import tqdm  # 添加进度条显示

class FeatureGenerator:
    def __init__(self):
        # 加载dlib模型
        self.detector = dlib.get_frontal_face_detector()
        self.shape_predictor = dlib.shape_predictor("dlib_module/shape_predictor_68_face_landmarks.dat")
        self.face_rec_model = dlib.face_recognition_model_v1("dlib_module/dlib_face_recognition_resnet_model_v1.dat")

    def extract_face_encoding(self, image):
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        faces = self.detector(rgb_image)
        
        if not faces:
            return None
            
        # 只使用第一个检测到的人脸
        shape = self.shape_predictor(rgb_image, faces[0])
        face_encoding = np.array(self.face_rec_model.compute_face_descriptor(rgb_image, shape))
        return face_encoding

    def generate_features(self, images_folder, output_file):
        face_encodings = []
        valid_image_paths = []  # 存储成功提取特征的图片路径
        
        # 获取所有图片文件
        image_files = [f for f in os.listdir(images_folder) 
                      if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        
        print(f"Processing {len(image_files)} images...")
        
        # 使用tqdm显示进度条
        for image_file in tqdm(image_files):
            image_path = os.path.join(images_folder, image_file)
            try:
                img = cv2.imread(image_path)
                if img is None:
                    continue
                    
                face_encoding = self.extract_face_encoding(img)
                if face_encoding is not None:
                    face_encodings.append(face_encoding)
                    valid_image_paths.append(image_path)
            except Exception as e:
                print(f"Error processing {image_file}: {str(e)}")
                
        # 保存特征向量和对应的图片路径
        if face_encodings:
            np.savez(output_file,
                    encodings=np.array(face_encodings),
                    image_paths=np.array(valid_image_paths))
            print(f"\nSuccessfully generated features for {len(face_encodings)} images")
            print(f"Features saved to {output_file}")
        else:
            print("No valid faces found in the images")

if __name__ == "__main__":
    generator = FeatureGenerator()
    # 设置图片文件夹和输出文件路径
    images_folder = "target"  # 替换为你的图片文件夹路径
    output_file = "face_features.npz"
    generator.generate_features(images_folder, output_file)