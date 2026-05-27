"""
Purpose:
    Runs YOLOv8 inference via ONNX Runtime and returns structured detections
    with proper post-processing including Non-Maximum Suppression (NMS).

Why proper post-processing matters:
    A raw YOLOv8 ONNX output contains thousands of candidate boxes, most of
    which are background or duplicates. Without post-processing:
        - One dog produces 5-20 "dog" detections
        - Each fires a separate Blynk event, MQTT message, and DB row
        - The Pi CPU spikes handling the cascade of downstream events
        - Cloudinary gets flooded with duplicate upload requests

    Proper post-processing pipeline:
        1. Decode raw tensor (confidence × class probability)
        2. Filter by CONFIDENCE_THRESHOLD
        3. Filter by TARGET_CLASSES (person, dog only)
        4. Apply NMS via cv2.dnn.NMSBoxes() to remove duplicate boxes
        5. Scale bounding boxes back to original image dimensions
        6. Return at most one result per class

Why NMS specifically:
    YOLOv8 (when exported without the NMS post-processing layer, which is
    the default) outputs raw boxes. The model may predict a dog 15 times
    with slightly different box coordinates. NMS keeps only the highest-
    confidence box and suppresses the rest based on IoU overlap.

    cv2.dnn.NMSBoxes() is available in opencv-python-headless which is
    already in requirements.txt — no additional dependencies needed.

ONNX output tensor format:
    YOLOv8 ONNX output shape: (1, 84, num_anchors)
        - 84 = 4 box coords (cx, cy, w, h) + 80 COCO class scores
        - Transposing to (num_anchors, 84) makes iteration natural
    Box format: centre-x, centre-y, width, height (all normalised to
    YOLO_INPUT_SIZE=640). Must be scaled back to the original image size.

Image resize:
    Input images from the camera (1920x1080) are resized to 640x640 for
    YOLO inference. The scaling ratio is tracked so bounding boxes can
    be mapped back to the original image coordinates.
"""

import os
import cv2
import numpy as np
import onnxruntime as ort

from config import (
    CONFIDENCE_THRESHOLD,
    NMS_THRESHOLD,
    YOLO_INPUT_SIZE,
    TARGET_CLASSES,
)
from logger_service import logger

# ── COCO class names (80 classes) ─────────────────────────────────────────────
COCO_CLASSES = [
    "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train",
    "truck", "boat", "traffic light", "fire hydrant", "stop sign",
    "parking meter", "bench", "bird", "cat", "dog", "horse", "sheep",
    "cow", "elephant", "bear", "zebra", "giraffe", "backpack", "umbrella",
    "handbag", "tie", "suitcase", "frisbee", "skis", "snowboard",
    "sports ball", "kite", "baseball bat", "baseball glove", "skateboard",
    "surfboard", "tennis racket", "bottle", "wine glass", "cup", "fork",
    "knife", "spoon", "bowl", "banana", "apple", "sandwich", "orange",
    "broccoli", "carrot", "hot dog", "pizza", "donut", "cake", "chair",
    "couch", "potted plant", "bed", "dining table", "toilet", "tv",
    "laptop", "mouse", "remote", "keyboard", "cell phone", "microwave",
    "oven", "toaster", "sink", "refrigerator", "book", "clock", "vase",
    "scissors", "teddy bear", "hair drier", "toothbrush",
]

# Resolve model path absolutely from this file's location.
# app/detector_service.py → project root → models/yolov8n.onnx
_BASE_DIR = os.getenv(
    "PROJECT_ROOT",
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
_MODEL_PATH = os.path.join(_BASE_DIR, "models", "yolov8n.onnx")


class DetectorService:
    """
    Runs YOLOv8 inference on a still image with full post-processing.

    Returns structured detections including bounding boxes, suitable for
    annotation, database logging, and event routing.

    Usage:
        detector   = DetectorService()
        detections = detector.detect("/path/to/image.jpg")

        # Each detection dict:
        # {
        #     "label":      "dog",
        #     "confidence": 0.87,
        #     "box":        [x1, y1, x2, y2]  ← pixel coords in original image
        # }
    """

    def __init__(self):
        if not os.path.exists(_MODEL_PATH):
            raise FileNotFoundError(
                f"ONNX model not found at {_MODEL_PATH}. "
                "Export yolov8n.onnx on your laptop and copy to models/."
            )

        logger.info(f"Loading ONNX model: {_MODEL_PATH}")

        self._session = ort.InferenceSession(
            _MODEL_PATH,
            providers=["CPUExecutionProvider"],
        )

        self._input_name = self._session.get_inputs()[0].name

        logger.info("ONNX model loaded.")

    # ── Public API ────────────────────────────────────────────────────────────

    def detect(self, image_path: str) -> list:
        """
        Run inference on a still image with full post-processing.

        Pipeline:
            load image → preprocess → ONNX inference → decode →
            confidence filter → class filter → NMS → scale boxes

        Args:
            image_path: path to the JPEG to analyse.

        Returns:
            List of detection dicts. Empty list if nothing found.
            Each dict: {"label": str, "confidence": float, "box": [x1,y1,x2,y2]}
        """
        if not image_path:
            return []

        try:
            # ── Load and preprocess ───────────────────────────────────────────
            image = cv2.imread(image_path)
            if image is None:
                logger.error(f"Could not read image: {image_path}")
                return []

            original_h, original_w = image.shape[:2]

            input_tensor, scale_x, scale_y = self._preprocess(image)

            # ── Run ONNX inference ────────────────────────────────────────────
            outputs = self._session.run(
                None,
                {self._input_name: input_tensor},
            )

            # ── Post-process ──────────────────────────────────────────────────
            detections = self._postprocess(
                outputs[0],
                scale_x,
                scale_y,
                original_w,
                original_h,
            )

            if detections:
                logger.info(
                    f"Detections after NMS: "
                    # Filter data inside current dictionary 'd' to exclude 'box' for cleaner logging.
                    # k represents the key, e.g., 'label' or 'confidence'.
                    # v represents the value corresponding to that key - 'dog', 'person', etc.
                    f"{[{k: v for k, v in d.items() if k != 'box'} for d in detections]}"
                )
            else:
                logger.info("YOLO: no target detections in this image.")

            return detections

        except Exception as error:
            logger.error(f"YOLO inference failed: {error}", exc_info=True)
            return []

    # ── Private helpers ───────────────────────────────────────────────────────

    def _preprocess(self, image: np.ndarray):
        """
        Resize image to YOLO input size and normalise pixel values.

        YOLOv8 expects: (1, 3, 640, 640) float32 tensor, values 0.0–1.0.

        Returns:
            (input_tensor, scale_x, scale_y)
            scale_x / scale_y are used to map boxes back to original coords.
        """
        original_h, original_w = image.shape[:2]

        # Resize to YOLO_INPUT_SIZE x YOLO_INPUT_SIZE.
        resized = cv2.resize(image, (YOLO_INPUT_SIZE, YOLO_INPUT_SIZE))

        # Convert BGR → RGB (OpenCV loads as BGR, YOLO expects RGB).
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)

        # Normalise to [0, 1] and convert to float32.
        normalised = rgb.astype(np.float32) / 255.0

        # Rearrange HWC → CHW and add batch dimension: (1, 3, 640, 640).
        tensor = np.transpose(normalised, (2, 0, 1))
        tensor = np.expand_dims(tensor, axis=0)

        # Scaling factors to map YOLO box coords back to original image size.
        scale_x = original_w / YOLO_INPUT_SIZE
        scale_y = original_h / YOLO_INPUT_SIZE

        return tensor, scale_x, scale_y

    def _postprocess(
        self,
        raw_output: np.ndarray,
        scale_x: float,
        scale_y: float,
        original_w: int,
        original_h: int,
    ) -> list:
        """
        Decode raw YOLO output, apply NMS, and return final detections.

        YOLOv8 ONNX raw output shape: (1, 84, num_anchors)
            84 = [cx, cy, w, h, class_0_score, ..., class_79_score]

        Steps:
            1. Transpose to (num_anchors, 84)
            2. Decode cx/cy/w/h → x1/y1/x2/y2
            3. Find highest-scoring class per anchor
            4. Filter by CONFIDENCE_THRESHOLD
            5. Filter by TARGET_CLASSES
            6. Apply NMS per class using cv2.dnn.NMSBoxes
            7. Scale boxes back to original image coordinates
        """
        # raw_output shape: (1, 84, num_anchors) → squeeze to (84, num_anchors)
        predictions = raw_output[0]            # (84, num_anchors)
        predictions = predictions.T            # (num_anchors, 84)

        # Separate box coords from class scores.
        box_coords   = predictions[:, :4]       # (num_anchors, 4): cx,cy,w,h
        class_scores = predictions[:, 4:]       # (num_anchors, 80)

        # Find the highest-scoring class for each anchor.
        class_ids     = np.argmax(class_scores, axis=1)   # (num_anchors,)
        confidences   = class_scores[np.arange(len(class_scores)), class_ids]

        # ── Per-class NMS ──────────────────────────────────────────────────────
        # We run NMS separately for each target class so a high-confidence
        # "person" box does not suppress a nearby "dog" box.
        final_detections = []

        for target_class in TARGET_CLASSES:
            target_class_id = COCO_CLASSES.index(target_class)

            # Mask: anchors matching this class AND above confidence threshold.
            mask = (class_ids == target_class_id) & (confidences >= CONFIDENCE_THRESHOLD)

            if not np.any(mask):
                continue

            class_boxes  = box_coords[mask]      # (n, 4) cx,cy,w,h
            class_scores_filtered = confidences[mask].tolist()

            # Convert cx,cy,w,h → x1,y1,w,h (cv2 NMS format).
            nms_boxes = []
            for cx, cy, w, h in class_boxes:
                x1 = int((cx - w / 2) * YOLO_INPUT_SIZE)
                y1 = int((cy - h / 2) * YOLO_INPUT_SIZE)
                bw = int(w * YOLO_INPUT_SIZE)
                bh = int(h * YOLO_INPUT_SIZE)
                nms_boxes.append([x1, y1, bw, bh])

            # Apply NMS — removes overlapping duplicate boxes.
            # Returns indices of boxes to KEEP.
            indices = cv2.dnn.NMSBoxes(
                nms_boxes,
                class_scores_filtered,
                CONFIDENCE_THRESHOLD,
                NMS_THRESHOLD,
            )

            if len(indices) == 0:
                continue

            # cv2.dnn.NMSBoxes returns either a list or ndarray depending
            # on OpenCV version — flatten to a simple list of ints.
            if isinstance(indices, np.ndarray):
                indices = indices.flatten().tolist()
            else:
                indices = [i for i in indices]

            for idx in indices:
                x1_nms, y1_nms, bw_nms, bh_nms = nms_boxes[idx]
                score = class_scores_filtered[idx]

                # Scale box coordinates back to original image dimensions.
                x1 = max(0, int(x1_nms * scale_x))
                y1 = max(0, int(y1_nms * scale_y))
                x2 = min(original_w, int((x1_nms + bw_nms) * scale_x))
                y2 = min(original_h, int((y1_nms + bh_nms) * scale_y))

                final_detections.append({
                    "label":      target_class,
                    "confidence": round(score, 3),
                    "box":        [x1, y1, x2, y2],
                })

        # Sort by confidence descending for cleaner logging.
        # key-lambda is an anonymous function that takes a detection dict d 
        # and returns the confidence score for sorting.
        final_detections.sort(key=lambda d: d["confidence"], reverse=True)

        return final_detections