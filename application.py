import os
import sys
import click
from dotenv import load_dotenv
import logging # Keep logging import

print("--- application.py: Top level START ---") # <-- ADD THIS

# ... rest of the imports ...
from app import create_app

logging.basicConfig(level=logging.INFO) # Ensure basic config
logger = logging.getLogger(__name__) # Get logger after basicConfig

print("--- application.py: Imports done, about to load dotenv ---") # <-- ADD THIS

dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(dotenv_path):
    print("--- application.py: Loading .env file ---") # <-- ADD THIS
    load_dotenv(dotenv_path)
else:
    print("--- application.py: .env file NOT found ---") # <-- ADD THIS

print("--- application.py: About to call create_app ---") # <-- ADD THIS
app = create_app(os.getenv("FLASK_CONFIG") or "DEV")
print("--- application.py: create_app finished, app object created ---") # <-- ADD THIS