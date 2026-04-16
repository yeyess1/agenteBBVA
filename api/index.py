import sys
import os

# Add the parent directory (root) to sys.path to find 'src'
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.main import app
