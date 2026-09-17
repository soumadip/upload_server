# Remove Python caches
find . -type d -name "__pycache__" -exec rm -rf {} +
rm -rf .pytest_cache/

# Remove editor swap/backup files
find . -type f -name ".*.un~" -delete

# Remove active databases and logs
rm -f lab_sessions.db
rm -f app.log app.debug.log

# (Optional) Clear all previous student uploads but keep the folders intact
find uploads/ -type f ! -name '.gitkeep' -delete
find test_cases/ -type f ! -name '.gitkeep' -delete
