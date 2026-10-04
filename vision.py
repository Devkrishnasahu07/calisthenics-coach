import cv2
import mediapipe as mp
import numpy as np

class FormTracker:
    def __init__(self):
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_pose = mp.solutions.pose
        # Initialize the MediaPipe pose model with standard confidence thresholds
        self.pose = self.mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)
        self.counter = 0
        self.stage = None

    def calculate_angle(self, a, b, c):
        """Calculates the angle between three points (e.g., shoulder, elbow, wrist)."""
        a = np.array(a) # First point
        b = np.array(b) # Mid point
        c = np.array(c) # End point
        
        radians = np.arctan2(c[1]-b[1], c[0]-b[0]) - np.arctan2(a[1]-b[1], a[0]-b[0])
        angle = np.abs(radians * 180.0 / np.pi)
        
        if angle > 180.0:
            angle = 360 - angle
            
        return angle

    def process_frame(self, frame):
        """Processes a single video frame, draws a skeletal overlay, and counts reps."""
        # Convert BGR (OpenCV format) to RGB (MediaPipe format)
        image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image.flags.writeable = False
        
        # Run the pose detection
        results = self.pose.process(image)
        
        # Convert back to BGR for screen rendering
        image.flags.writeable = True
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

        try:
            landmarks = results.pose_landmarks.landmark
            
            # Extract coordinates for the left arm
            shoulder = [landmarks[self.mp_pose.PoseLandmark.LEFT_SHOULDER.value].x, 
                        landmarks[self.mp_pose.PoseLandmark.LEFT_SHOULDER.value].y]
            elbow = [landmarks[self.mp_pose.PoseLandmark.LEFT_ELBOW.value].x, 
                     landmarks[self.mp_pose.PoseLandmark.LEFT_ELBOW.value].y]
            wrist = [landmarks[self.mp_pose.PoseLandmark.LEFT_WRIST.value].x, 
                     landmarks[self.mp_pose.PoseLandmark.LEFT_WRIST.value].y]
            
            # Calculate the elbow joint angle
            angle = self.calculate_angle(shoulder, elbow, wrist)
            
            # Rep counting logic (Triggers when the arm bends and extends)
            if angle > 160:
                self.stage = "extended"
            if angle < 50 and self.stage == 'extended':
                self.stage = "flexed"
                self.counter += 1
                
        except:
            pass # Fails gracefully if the body parts aren't fully visible

        # Draw the generated skeletal landmarks directly onto the image
        if results.pose_landmarks:
            self.mp_drawing.draw_landmarks(image, results.pose_landmarks, self.mp_pose.POSE_CONNECTIONS)
            
        return image, self.counter, self.stage