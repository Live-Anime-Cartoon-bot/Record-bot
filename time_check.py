
from datetime import datetime

# Function to check recording time
def check_recording_time(timess):
    try:
        # Parse the requested recording time
        requested_time = datetime.strptime(timess, "%H:%M:%S")
        max_time = datetime.strptime("00:50:00", "%H:%M:%S")  # 50-minute limit

        # Check if the requested time exceeds the 50-minute limit
        if requested_time > max_time:
            return False, "Recording time exceeds the 50-minute limit."
        
        return True, None  # Time is within limit

    except ValueError:
        return False, "Invalid timestamp format. Use `hh:mm:ss`"
