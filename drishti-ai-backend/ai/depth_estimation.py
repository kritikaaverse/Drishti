"""No monocular/bbox distance guesses. Add a calibrated, validated depth adapter separately."""
class DepthEstimator:
    validated = False
    def estimate(self, frame, detections):
        for detection in detections:
            detection.distance = None
            detection.distance_type = 'not_available'
        return detections
