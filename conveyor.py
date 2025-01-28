import time
import serial
import requests
import numpy as np
from pprint import pprint
import cv2
import sqlite3, uuid
from requests.auth import HTTPBasicAuth
from datetime import datetime

conn = sqlite3.connect('PICO_CHECK.db')
cursor = conn.cursor()

create_table_query ='''
CREATE TABLE IF NOT EXISTS PRODUCT (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    datetime TEXT,
    uuid TEXT UNIQUE,
    is_defective INTEGER,
    defect_reason TEXT
)
'''
cursor.execute(create_table_query)
conn.commit()
# Serial Port 설정
ser = serial.Serial("/dev/ttyACM0", 9600)

# API endpoint
#ver 8
api_url = "https://suite-endpoint-api-apne2.superb-ai.com/endpoints/8aeb480e-7943-4103-88f6-1b1a902f0765/inference"
ACCESS_KEY = "87Ooe3vJlV859berMYnCja8GUJpepPue2SCPwzVl"

# 필요한 객체 리스트
required_keys = ['RASPBERRY PICO', 'CHIPSET', 'BOOTSEL', 'USB', 'HOLE', 'OSCILLIATOR']
def insert_data(datetime_value,uuid_value, is_defective,defect_reason=None):
    insert_query = '''
    INSERT INTO PRODUCT (datetime,uuid,is_defective,defect_reason)
    VALUES (?, ?, ?, ?)
    '''
    cursor.execute(insert_query, (datetime_value, uuid_value, is_defective, defect_reason))
    conn.commit()


def crop_img(img, size_dict):
    x = size_dict["x"]
    y = size_dict["y"]
    w = size_dict["width"]
    h = size_dict["height"]
    img = img[y: y + h, x: x + w]
    return img

def inference_request(img: np.array, api_url: str):
    _, img_encoded = cv2.imencode(".jpg", img)

    try:
        response = requests.post(
            api_url,
            auth=HTTPBasicAuth("kdt2024_1-17", ACCESS_KEY),
            headers={"Content-Type": "image/jpeg"},
            data=img_encoded.tobytes(),
        )
        if response.status_code == 200:
            #pprint(response.json())
            return response.json()
        else:
            print(f"Failed to send image. Status code: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"Error sending request: {e}")
        return None

def draw_boxes(frame, objects):
    # 클래스별 색상 정의 (B, G, R 형식)
    class_colors = {
        'RASPBERRY PICO': (0, 0, 255),    # 빨강
        'CHIPSET': (0, 165, 255),         # 주황
        'BOOTSEL': (0, 255, 255),         # 노랑
        'USB': (0, 255, 0),               # 초록
        'HOLE': (255, 0, 0),              # 파랑
        'OSCILLIATOR': (255, 0, 255)      # 보라
    }

    for obj in objects:
        # Extract class and bounding box
        name = obj['class']
        start_point = (obj['box'][0], obj['box'][1])
        end_point = (obj['box'][2], obj['box'][3])

        # 해당 클래스의 색상 가져오기
        color = class_colors.get(name, (0, 255, 0))  # 기본값은 초록색

        # Draw bounding box
        thickness = 1
        cv2.rectangle(frame, start_point, end_point, color, thickness)

        # Draw class label
        text = name
        position = (start_point[0], start_point[1] - 10)
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.5
        text_color = color  # 텍스트도 같은 색상으로
        text_thickness = 1
        cv2.putText(frame, text, position, font, font_scale, text_color, text_thickness, cv2.LINE_AA)

def check_objects(objects):
    name_dict = {}
    missing_counts = {key: 0 for key in required_keys}
    missing_objects = []
    is_defective = 0
    defect_reason = None
    datetime_value = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    uuid_value = str(uuid.uuid4())
    
    for obj_name in objects:
        name = obj_name['class']
        confidence = obj_name.get('score',0)
        if name == "USB" and confidence > 0.9:
            name_dict[name] = name_dict.get(name,0) + 1
        elif name == "USB" and confidence <= 0.9:
            #print(f'low confidence USB : {confidence}')
            pass
        if name != 'USB':
            name_dict[name] = name_dict.get(name, 0) + 1

    for key in required_keys:
        if key not in name_dict:
            missing_counts[key] += 1
            missing_objects.append(key)

    if missing_objects:
        #print(f"Missing Objects: {missing_objects}")
        is_defective = 1
        defect_reason = f"Missing object {missing_objects}"
        insert_data(datetime_value,uuid_value,is_defective,defect_reason)
        return False, name_dict

    if ('HOLE' not in name_dict or name_dict['HOLE'] != 4) or \
       any(name_dict.get(key, 0) != 1 for key in required_keys if key != 'HOLE'):
       is_defective = 1
       defect_reason = f"Incorrect count {name_dict}"
       insert_data(datetime_value,uuid_value,is_defective,defect_reason)
       #print(f"Incorrect Object Counts: {name_dict}")
       return False, name_dict
    insert_data(datetime_value,uuid_value,is_defective,defect_reason)
    return True, name_dict

# 카메라 스트림 열기
cam = cv2.VideoCapture(0)

if not cam.isOpened():
    print("Camera Error")
    exit(-1)

try:
    while True:
        # Serial 데이터 확인
        data = ser.read()
        #print(data)
        
        if data == b"0":
            start_time = time.time()
            time.sleep(0.1)
            # 카메라 버퍼 비우기
            for _ in range(4):  # 버퍼를 비우기 위해 5번 프레임 읽기
                cam.read()

            # 최신 프레임 읽기
            ret, frame = cam.read()
            if not ret:
                print("Failed to grab frame")
                continue

            # Crop the image if needed
            crop_info = {"x": 300, "y": 0, "width": 400, "height": 300}
            img = crop_img(frame, crop_info)

            # Perform inference
            result = inference_request(img, api_url)

            # If result is not None, process and draw bounding boxes
            if result:
                objects = result.get("objects", [])
                is_good, name_dict = check_objects(objects)
                
                draw_boxes(img, objects)
                if is_good:
                    print("Good Product Detected!")
                else:
                    print("Bad Product Detected!")

            # Display the image with bounding boxes
            cv2.imshow("Object Detection", img)
            cv2.waitKey(1)
            ser.write(b"1")  # Send signal for good product
            total_time = time.time() - start_time
            print(f"Processing Time: {total_time:.2f} seconds")

finally:
    # 리소스 해제
    cam.release()
    conn.close()
    cv2.destroyAllWindows()
