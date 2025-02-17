import cv2
import mediapipe as mp
import time
import torch
from ultralytics import YOLO

debug = False

def detection_window ():
    # Load a pretrained YOLO model trained on HaGRID
    gesture_model = YOLO("models\YOLOv10n_gestures.pt")

    if (torch.cuda.is_available()):
        print("CUDA available")
        gesture_model.to('cuda')
    else:
        print("CUDA not available")

    mp_drawing = mp.solutions.drawing_utils
    mp_drawing_styles = mp.solutions.drawing_styles
    mp_hands = mp.solutions.hands

    # Start webcam
    cap = cv2.VideoCapture(0)

    with mp_hands.Hands(
        model_complexity=0,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5) as hands:
        while cap.isOpened():   
            frame_start_time = time.time()
            success, image = cap.read()
            if not success:
                print("Ignoring empty camera frame.")
                continue

            # To improve performance, mark the image as not writeable to pass by reference.
            image.flags.writeable = False
            mediapipe_results = hands.process(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
            image.flags.writeable = True
            
            #If there are hands in the frame
            if mediapipe_results.multi_hand_landmarks:
                gesture_result = gesture_model(image, verbose=False)[0]
                image = gesture_result.plot()

                #Uncomment to draw hand landmarks
                # for hand_landmarks in mediapipe_results.multi_hand_landmarks:
                #     mp_drawing.draw_landmarks(
                #     image,
                #     hand_landmarks,
                #     mp_hands.HAND_CONNECTIONS,
                #     mp_drawing_styles.get_default_hand_landmarks_style(),
                #     mp_drawing_styles.get_default_hand_connections_style())
            cv2.putText(image, ("FPS: " + str(round((1.0 / (time.time() - frame_start_time)), 2))), (0,40), cv2.FONT_HERSHEY_SIMPLEX , 1, (0, 0, 255), 1, cv2.LINE_8)

            if debug:
                cv2.imshow('Gesture Hotkey Debug', image)
            else:
                cv2.destroyAllWindows()

            if cv2.waitKey(5) & 0xFF == 27:
                break
    cap.release()
    cv2.destroyAllWindows()


def toggle_debug():
    global debug
    debug = not debug