"""Check if TGOS recovers the 8 failed full-address cases."""
import sys, logging
sys.path.insert(0, ".")
logging.basicConfig(level=logging.INFO, format="%(message)s")
from scripts.run_address_benchmark import run_benchmark
run_benchmark()
