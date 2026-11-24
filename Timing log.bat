@echo off
rem UCEC FT3000 with the timing log on: it writes timing_log.jsonl in your data folder (Saved Games\UCEC FT3000 -
rem the console says where). See "Timing log" in ed_target_board.py.
rem Close the board as usual (Exit on the page, or this window) when you have flown your run.
cd /d "%~dp0"
if exist "%~dp0python\python.exe" (
  "%~dp0python\python.exe" "%~dp0ed_target_board.py" --timing-log %*
) else (
  where py >nul 2>nul
  if not errorlevel 1 (
    py "%~dp0ed_target_board.py" --timing-log %*
  ) else (
    python "%~dp0ed_target_board.py" --timing-log %*
  )
)
echo.
echo The timing log is timing_log.jsonl, in your data folder (its place is shown above).
pause
