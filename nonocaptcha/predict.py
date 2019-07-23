import cv2
import numpy as np
from PIL import Image
from nonocaptcha import package_dir
from nonocaptcha.util import get_page, save_file


# It need better
def is_marked(img_path):
    img = Image.open(img_path).convert('RGB')
    w, h = img.size
    for i in range(w):
        for j in range(h):
            r, g, b = img.getpixel((i,j))
            # Detect Color Blue
            if r == 0 and g == 0 and b == 254:
                return True
    return False


def get_output_layers(net):
    layer_names = net.getLayerNames()
    output_layers = [layer_names[i[0] - 1] for i in net.getUnconnectedOutLayers()]
    return output_layers


def draw_prediction(img, x, y, x_plus_w, y_plus_h):
    color = 256  # Blue
    # Paint Rectangle Blue
    cv2.rectangle(img, (x, y), (x_plus_w, y_plus_h), color, cv2.FILLED)


async def predict(file, obj=None):
    weight_file = f"{package_dir}/models/yolov3.weights"
    file_names = f"{package_dir}/models/yolov3.txt"
    file_cfg = f"{package_dir}/models/yolov3.cfg"

    image = cv2.imread(file)
    width = image.shape[1]
    height = image.shape[0]
    scale = 0.00392

    with open(file_names, 'r') as f:
        classes = [line.strip() for line in f.readlines()]

    if obj is None:
        try:
            net = cv2.dnn.readNet(weight_file, file_cfg)
        except Exception as ex:
            yolo_url = 'https://pjreddie.com/media/files/yolov3.weights'
            print('Downloading Yolo v3 Weight ...')
            weight = await get_page(yolo_url, None, None, binary=True)
            # Save Image
            await save_file(weight_file, weight, binary=True)
            raise Exception(ex)
        blob = cv2.dnn.blobFromImage(image, scale, (416, 416), (0, 0, 0), True, crop=False)
        net.setInput(blob)
        outs = net.forward(get_output_layers(net))
        classes_names = []
        for out in outs:
            for detection in out:
                scores = detection[5:]
                class_id = np.argmax(scores)
                confidence = scores[class_id]
                if confidence > 0.5:
                    classes_names.append(classes[class_id])
        return classes_names  # Return all names object in the images
    else:
        out_path = f"{package_dir}/tmp/{hash(file)}.jpg"

        try:
            net = cv2.dnn.readNet(weight_file, file_cfg)
        except Exception as ex:
            yolo_url = 'https://pjreddie.com/media/files/yolov3.weights'
            print('Downloading Yolo v3 Weight ...')
            weight = await get_page(yolo_url, None, None, binary=True)
            # Save Image
            await save_file(weight_file, weight, binary=True)
            raise Exception(ex)
        blob = cv2.dnn.blobFromImage(image, scale, (416, 416), (0, 0, 0), True, crop=False)
        net.setInput(blob)
        outs = net.forward(get_output_layers(net))

        class_ids = []
        confidences = []
        boxes = []
        conf_threshold = 0.5
        nms_threshold = 0.4

        for out in outs:
            for detection in out:
                scores = detection[5:]
                class_id = np.argmax(scores)
                confidence = scores[class_id]
                if confidence > 0.5:
                    center_x = int(detection[0] * width)
                    center_y = int(detection[1] * height)
                    w = int(detection[2] * width)
                    h = int(detection[3] * height)
                    x = center_x - w / 2
                    y = center_y - h / 2
                    class_ids.append(class_id)
                    confidences.append(float(confidence))
                    boxes.append([x, y, w, h])

        indices = cv2.dnn.NMSBoxes(boxes, confidences, conf_threshold, nms_threshold)
        out = False
        for i in indices:
            if obj == 'vehicles' and (classes[class_ids[int(i)]] == 'car' or classes[class_ids[int(i)]] == 'truck'):
                out = out_path
                i = i[0]
                box = boxes[i]
                x = box[0]
                y = box[1]
                w = box[2]
                h = box[3]
                draw_prediction(image, round(x), round(y), round(x + w), round(y + h))
            elif classes[class_ids[int(i)]] == obj:
                out = out_path
                i = i[0]
                box = boxes[i]
                x = box[0]
                y = box[1]
                w = box[2]
                h = box[3]
                draw_prediction(image, round(x), round(y), round(x + w), round(y + h))
            # Save Image
        if out:
            cv2.imwrite(out_path, image)
        return out  # Return path of images or False if not found object
