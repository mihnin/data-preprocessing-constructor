import json
import numpy as np

class NumpyJSONEncoder(json.JSONEncoder):
    """
    Custom JSON encoder for NumPy data types.

    This encoder handles the serialization of common NumPy types that are not
    natively supported by Python's `json` module. It converts them to standard
    Python types.
    - np.integer, np.int64 -> int
    - np.floating, np.float64 -> float (NaN and Infinity are converted to None)
    - np.ndarray -> list
    """
    def default(self, obj):
        if isinstance(obj, (np.integer, np.int64)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float64)):
            # Handle special float values like NaN and Infinity
            if np.isnan(obj) or np.isinf(obj):
                return None
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()

        # Let the base class default method raise the TypeError for other types
        return super().default(obj)