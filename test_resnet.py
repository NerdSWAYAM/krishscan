import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
import tensorflow as tf

model_path = os.path.join(os.getcwd(), 'MLmodels', 'resnet50_transfer_best.h5')
model = tf.keras.models.load_model(model_path)
print("ResNet output shape:", model.output_shape)
