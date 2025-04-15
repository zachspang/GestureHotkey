import os
os.environ["OPENCV_LOG_LEVEL"] = "E"
os.environ["OPENCV_VIDEOIO_MSMF_ENABLE_HW_TRANSFORMS"] = "0"
import cv2
import mediapipe as mp
import time
import torch
import ultralytics
import ultralytics.engine.results

debug = False
detections = []
cam_index = 0

def detection_window ():
    # Load a pretrained YOLO model trained on HaGRID
    gesture_model = ultralytics.YOLO("models\YOLOv10n_gestures.pt")

    if (torch.cuda.is_available()):
        print("CUDA available")
        gesture_model.to('cuda')
    else:
        print("CUDA not available")

    mp_drawing = mp.solutions.drawing_utils
    mp_drawing_styles = mp.solutions.drawing_styles
    mp_hands = mp.solutions.hands

    # Start webcam
    curr_cam_index = cam_index
    cap = cv2.VideoCapture(cam_index)

    with mp_hands.Hands(
        model_complexity=0,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5) as hands:
        while cap.isOpened(): 
            if cam_index != curr_cam_index:
                if cam_index == -1:
                    cap.release()
                else:
                    curr_cam_index = cam_index
                    cap.release()
                    cap = cv2.VideoCapture(cam_index)

            frame_start_time = time.time()
            success, image = cap.read()
            if not success:
                continue

            # To improve performance, mark the image as not writeable to pass by reference.
            image.flags.writeable = False
            mediapipe_results = hands.process(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
            image.flags.writeable = True

            global detections
            #If there are hands in the frame
            if mediapipe_results.multi_hand_landmarks:
                gesture_result:ultralytics.engine.results.Results = gesture_model(image, verbose=False)[0]
                detections = gesture_result.summary()
                
                if debug:
                    image = gesture_result.plot()
                    #Uncomment to draw hand landmarks
                    # for hand_landmarks in mediapipe_results.multi_hand_landmarks:
                    #     mp_drawing.draw_landmarks(
                    #     image,
                    #     hand_landmarks,
                    #     mp_hands.HAND_CONNECTIONS,
                    #     mp_drawing_styles.get_default_hand_landmarks_style(),
                    #     mp_drawing_styles.get_default_hand_connections_style())
            else:
                detections = []
                
            if debug:
                cv2.putText(image, ("FPS: " + str(round((1.0 / (time.time() - frame_start_time)), 2))), (0,40), cv2.FONT_HERSHEY_SIMPLEX , 1, (0, 0, 255), 1, cv2.LINE_8)
                cv2.imshow('Gesture Hotkey Debug', image)
            else:
                cv2.destroyAllWindows()

            if cv2.waitKey(1) & 0xFF == 27:
                break
    cap.release()
    cv2.destroyAllWindows()

def get_detections():
    global detections
    return detections

def toggle_debug():
    global debug
    debug = not debug

def set_cam(new_index):
    global cam_index
    cam_index = new_index

def get_cam():
    return cam_index