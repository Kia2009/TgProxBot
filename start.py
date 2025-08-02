#!/usr/bin/env python3
import os
import sys
import signal
import logging
from bot import main

def signal_handler(signum, frame):
    logging.info(f"Received signal {signum}")
    sys.exit(0)

if __name__ == "__main__":
    # Handle termination signals gracefully
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    # Set PORT environment variable for Koyeb
    os.environ.setdefault('PORT', '8080')
    
    try:
        main()
    except Exception as e:
        logging.error(f"Fatal error: {e}")
        sys.exit(1)