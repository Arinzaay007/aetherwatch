"""
AetherWatch — YOLO Object Detection Engine
Uses Ultralytics YOLOv8 for real-time object detection on camera frames.

Features:
- Auto device selection: CUDA → MPS (Apple Silicon) → CPU
- Runs in background thread to keep dashboard responsive
- Anomaly detection: crowd clustering, stopped vehicles, unusual density
- Graceful degradation if ultralytics not available

Performance targets:
- GPU (CUDA/MPS): ~30-60 FPS
- CPU (4-core):   ~5-15 FPS on 640px images
"""

import time
import threading
import queue
from typing import Optional
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from utils.logger import get_logger
from config import settings

log = get_logger(__name__)

# ── YOLO Availability Check ───────────────────────────────────────────────────

try:
    from ultralytics import YOLO
    import torch
    YOLO_AVAILABLE = True
    log.info("Ultralytics YOLO available ✓")
except ImportError:
    YOLO_AVAILABLE = False
    log.warning("Ultralytics not installed — YOLO detection disabled. Run: pip install ultralytics")


# ── Device Detection ──────────────────────────────────────────────────────────

def detect_best_device() -> str:
    """Return the best available inference device."""
    if not YOLO_AVAILABLE:
        return "cpu"
    try:
        import torch
        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            log.info(f"CUDA GPU detected: {gpu_name}")
            return "cuda"
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            log.info("Apple Silicon MPS detected")
            return "mps"
    except Exception:
        pass
    log.info("Using CPU for YOLO inference")
    return "cpu"


# ── Detection Result ──────────────────────────────────────────────────────────

class Detection:
    """A single detected object."""
    def __init__(self, class_id: int, class_name: str, confidence: float, bbox: tuple):
        self.class_id = class_id
        self.class_name = class_name
        self.confidence = confidence
        self.bbox = bbox  # (x1, y1, x2, y2) in pixels

    def to_dict(self) -> dict:
        return {
            "class": self.class_name,
            "confidence": round(self.confidence, 3),
            "bbox": self.bbox,
        }


class DetectionResult:
    """Full detection result for a single frame."""
    def __init__(
        self,
        detections: list[Detection],
        annotated_image: Optional[Image.Image],
        inference_ms: float,
        anomalies: list[str],
        is_live: bool = True,
    ):
        self.detections = detections
        self.annotated_image = annotated_image
        self.inference_ms = inference_ms
        self.anomalies = anomalies
        self.is_live = is_live
        self.timestamp = time.time()

    @property
    def counts(self) -> dict[str, int]:
        """Return per-class detection counts."""
        counts: dict[str, int] = {}
        for d in self.detections:
            counts[d.class_name] = counts.get(d.class_name, 0) + 1
        return counts

    @property
    def person_count(self) -> int:
        return self.counts.get("person", 0)

    @property
    def vehicle_count(self) -> int:
        return sum(self.counts.get(c, 0) for c in ["car", "truck", "bus", "motorcycle"])


# ── YOLO Detector ─────────────────────────────────────────────────────────────

class YOLODetector:
    """
    Thread-safe YOLOv8 detector with async queue-based processing.
    Load once, reuse across all frames.
    """
    
    _instance: Optional["YOLODetector"] = None
    _lock = threading.Lock()
    
    def __init__(self):
        self.model = None
        self.device = detect_best_device()
        self.is_loaded = False
        self._result_cache: dict[str, DetectionResult] = {}
        self._load_model()
    
    @classmethod
    def get_instance(cls) -> "YOLODetector":
        """Singleton pattern for model reuse (expensive to load)."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance
    
    def _load_model(self):
        """Load YOLOv8 model. Downloads automatically on first run."""
        if not YOLO_AVAILABLE:
            log.warning("YOLO not available — running in passthrough mode")
            return
        
        try:
            log.info(f"Loading YOLO model: {settings.YOLO_MODEL_NAME} on {self.device}")
            self.model = YOLO(settings.YOLO_MODEL_NAME)
            # Warm up
            dummy = np.zeros((640, 640, 3), dtype=np.uint8)
            self.model(dummy, device=self.device, verbose=False)
            self.is_loaded = True
            log.info(f"YOLO model loaded ✓ (device={self.device})")
        except Exception as e:
            log.error(f"Failed to load YOLO model: {e}")
            self.is_loaded = False
    
    def detect(self, image: Image.Image, camera_id: str = "default") -> DetectionResult:
        """
        Run object detection on a PIL image.
        
        Args:
            image:     PIL Image (RGB)
            camera_id: Used for per-camera caching
        
        Returns:
            DetectionResult with annotated image and detection list
        """
        if not self.is_loaded or self.model is None:
            return self._passthrough_result(image)
        
        start = time.time()
        
        try:
            img_array = np.array(image)
            results = self.model(
                img_array,
                device=self.device,
                conf=settings.YOLO_CONFIDENCE,
                iou=settings.YOLO_IOU_THRESHOLD,
                imgsz=settings.YOLO_IMG_SIZE,
                verbose=False,
            )
            
            detections = []
            result = results[0]
            
            for box in result.boxes:
                class_id = int(box.cls[0].item())
                confidence = float(box.conf[0].item())
                x1, y1, x2, y2 = [int(v) for v in box.xyxy[0].tolist()]
                class_name = result.names.get(class_id, str(class_id))
                
                # Filter to classes of interest (or show all)
                detections.append(Detection(class_id, class_name, confidence, (x1, y1, x2, y2)))
            
            inference_ms = (time.time() - start) * 1000
            annotated = self._draw_detections(image.copy(), detections)
            anomalies = self._check_anomalies(detections, image.size)
            
            det_result = DetectionResult(
                detections=detections,
                annotated_image=annotated,
                inference_ms=inference_ms,
                anomalies=anomalies,
                is_live=True,
            )
            self._result_cache[camera_id] = det_result
            return det_result
        
        except Exception as e:
            log.error(f"YOLO inference error: {e}")
            return self._passthrough_result(image)
    
    def _draw_detections(self, image: Image.Image, detections: list[Detection]) -> Image.Image:
        """Draw bounding boxes and labels on image."""
        draw = ImageDraw.Draw(image)
        
        # Colour per class
        class_colors = {
            "person": "#FF4444",
            "car": "#44FF44",
            "truck": "#FF8800",
            "bus": "#FF8800",
            "motorcycle": "#00FFFF",
            "bicycle": "#FFFF00",
            "airplane": "#FF44FF",
            "boat": "#4488FF",
        }
        
        try:
            font = ImageFont.load_default()
        except Exception:
            font = None
        
        for det in detections:
            x1, y1, x2, y2 = det.bbox
            color = class_colors.get(det.class_name, "#FFFFFF")
            
            # Box
            draw.rectangle([x1, y1, x2, y2], outline=color, width=2)
            
            # Label background
            label = f"{det.class_name} {det.confidence:.0%}"
            label_h = 14
            draw.rectangle([x1, y1 - label_h, x1 + len(label) * 6 + 4, y1], fill=color)
            draw.text((x1 + 2, y1 - label_h), label, fill=(0, 0, 0), font=font)
        
        # Stats overlay (bottom right)
        counts = {}
        for d in detections:
            counts[d.class_name] = counts.get(d.class_name, 0) + 1
        
        if counts:
            stats = "  ".join(f"{k}:{v}" for k, v in sorted(counts.items()))
            w, h = image.size
            draw.rectangle([0, h - 20, w, h], fill=(0, 0, 0))
            draw.text((4, h - 16), f"Detected: {stats}", fill=(100, 255, 100), font=font)
        
        return image
    
    def _check_anomalies(self, detections: list[Detection], img_size: tuple) -> list[str]:
        """
        Detect anomalous patterns in the detection results.
        Returns list of anomaly description strings.
        """
        anomalies = []
        counts = {}
        for d in detections:
            counts[d.class_name] = counts.get(d.class_name, 0) + 1
        
        # Anomaly 1: Crowd (many people in frame)
        persons = counts.get("person", 0)
        if persons >= settings.ANOMALY_CROWD_THRESHOLD:
            anomalies.append(f"🚨 Large crowd detected: {persons} people in frame")
        
        # Anomaly 2: Vehicle cluster
        vehicles = sum(counts.get(c, 0) for c in ["car", "truck", "bus", "motorcycle"])
        if vehicles >= settings.ANOMALY_VEHICLE_CLUSTER:
            anomalies.append(f"⚠️ High vehicle density: {vehicles} vehicles")
        
        # Anomaly 3: Aircraft at unexpected location (ground camera seeing airplane close)
        if counts.get("airplane", 0) > 0:
            # Check if airplane bbox is large (meaning it's close/low)
            for d in detections:
                if d.class_name == "airplane":
                    box_area = (d.bbox[2] - d.bbox[0]) * (d.bbox[3] - d.bbox[1])
                    img_area = img_size[0] * img_size[1]
                    if box_area / img_area > 0.05:  # >5% of frame
                        anomalies.append("⚠️ Large aircraft close to ground camera")
        
        return anomalies
    
    def _passthrough_result(self, image: Image.Image) -> DetectionResult:
        """Return a no-detection result when YOLO is unavailable."""
        draw = ImageDraw.Draw(image)
        w, h = image.size
        draw.rectangle([0, h - 20, w, h], fill=(0, 0, 0))
        try:
            font = ImageFont.load_default()
        except Exception:
            font = None
        status = "YOLO not loaded" if not self.is_loaded else "Detection disabled"
        draw.text((4, h - 16), f"⚪ {status}", fill=(150, 150, 150), font=font)
        
        return DetectionResult(
            detections=[],
            annotated_image=image,
            inference_ms=0.0,
            anomalies=[],
            is_live=False,
        )
    
    @property
    def device_info(self) -> str:
        status = "✓ Loaded" if self.is_loaded else "✗ Not loaded"
        return f"{settings.YOLO_MODEL_NAME} on {self.device} — {status}"
