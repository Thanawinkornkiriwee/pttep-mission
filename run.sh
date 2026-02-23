#!/bin/bash

# Name of the tmux session
SESSION="pttep_mission"

# Start a new detached tmux session
tmux new-session -d -s $SESSION

# Terminal 1 (Left Pane): simulate_stream.py
tmux send-keys -t $SESSION:0 "cd /home/engineer00/winworkspace/PTTEP/MissionAI/test" C-m
tmux send-keys -t $SESSION:0 "conda activate yolo_env" C-m
tmux send-keys -t $SESSION:0 "python simulate_stream.py" C-m

# Split the window horizontally (side-by-side)
tmux split-window -h -t $SESSION:0

# Terminal 2 (Right Pane): main script
tmux send-keys -t $SESSION:0.1 "cd /home/engineer00/winworkspace/PTTEP/MissionAI/" C-m
tmux send-keys -t $SESSION:0.1 "conda activate yolo_env" C-m
# Note: Assuming 'main.py' if 'main' doesn't execute
tmux send-keys -t $SESSION:0.1 "python main.py --mode=video" C-m

# Attach to the session so you can see the output
tmux attach-session -t $SESSION