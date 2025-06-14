import socket
from pynput.keyboard import Key, Listener

# Configuration
UDP_IP = "localhost"  # Replace with receiver's IP address
UDP_PORT = 7000       # Replace with receiver's port

# Create UDP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

def send_key_event(event_type, key):
    """Send key events over UDP"""
    try:
        if isinstance(key, Key):
            # Handle special keys (Shift, Ctrl, etc.)
            key_str = key.name
        else:
            # Handle regular characters
            key_str = key.char
    except AttributeError:
        # Fallback for keys without a char attribute
        key_str = str(key)
    
    # Construct and send message {event_type}, {key_str}
    message = f"{key_str}"
    sock.sendto(message.encode('utf-8'), (UDP_IP, UDP_PORT))

def on_press(key):
    send_key_event("press", key)

# def on_release(key):
#     send_key_event("release", key)

# Start keyboard listener on_release=on_release
with Listener(on_press=on_press) as listener:
    print(f"Sending key events to {UDP_IP}:{UDP_PORT}. Press ESC to stop.")
    listener.join()