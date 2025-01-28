import requests
from requests.auth import HTTPBasicAuth
import cv2
import matplotlib.pyplot as plt
import os


URL = ""
ACCESS_KEY = ""

thickness = 1
folder = '/content/test_images/'
file_list = os.listdir(folder)
jpg_file = [f for f in file_list if f.endswith('.jpg')]

normal = 0
normal_name = []

abnormal = 0
abnormal_name = []

for name in jpg_file:
  y = 15
  class_num = [0,0,0,0,0,0]
  IMAGE_FILE_PATH = cv2.imread(os.path.join(folder, name))
  image = open(os.path.join(folder, name), "rb").read()

  response = requests.post(
    url=URL,
    auth=HTTPBasicAuth("kdt2024_1-17", ACCESS_KEY),
    headers={"Content-Type": "image/jpeg"},
    data=image,
  )
  data = response.json()

  for temp in [obj for obj in data['objects']]:
    start_point = (temp['box'][0], temp['box'][1])
    end_point = (temp['box'][2], temp['box'][3])
    cv2.rectangle(IMAGE_FILE_PATH, start_point, end_point, (0,255,0), thickness)
    # cv2.putText(IMAGE_FILE_PATH,temp['class'],start_point,cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,0,255), thickness)

    if temp['class'] == 'RASPBERRY PICO':
      class_num[0] += 1
    elif temp['class'] == 'OSCILLIATOR':
      class_num[1] += 1
    elif temp['class'] == 'USB':
      class_num[2] += 1
    elif temp['class'] == 'CHIPSET':
      class_num[3] += 1
    elif temp['class'] == 'BOOTSEL':
      class_num[4] += 1
    elif temp['class'] == 'HOLE':
      class_num[5] += 1

  if class_num[0] == 1 and class_num[1] == 1 and class_num[2] == 1 and class_num[3] == 1 and class_num[4] == 1 and class_num[5] == 4:
    normal += 1
    normal_name.append(name)
  else:
    abnormal += 1
    abnormal_name.append(name)

  for i, class_name in enumerate(['RASPBERRY PICO', 'OSCILLIATOR', 'USB', 'CHIPSET', 'BOOTSEL', 'HOLE']):
    cv2.putText(IMAGE_FILE_PATH,class_name+str(class_num[i]),(0,y),cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,0,255), thickness)
    y += 15

  img_rgb = cv2.cvtColor(IMAGE_FILE_PATH, cv2.COLOR_BGR2RGB)

  plt.imshow(img_rgb)
  plt.axis('off')
  plt.show()
  print(name)

print(f"normal_num : {normal}")
print(normal_name)
print(f"abnormal_num : {abnormal}")
print(abnormal_name)
