#!/bin/bash
echo "=== Starting Full Data Update ==="

echo "1. Updating general data (update_data.py)..."
python3 update_data.py

echo "2. Updating screener data (update_screener.py)..."
python3 update_screener.py

echo "3. Updating earnings trend data (update_earnings.py)..."
python3 update_earnings.py

echo "=== All Updates Completed Successfully! ==="
