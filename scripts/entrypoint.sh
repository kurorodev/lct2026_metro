#!/usr/bin/env bash
set -eo pipefail
source /opt/ros/humble/setup.bash
set -u
case "${1:-help}" in
  run|serve) exec python3 -m metro_guard.cli "$@" ;;
  node) shift; exec python3 -m metro_guard.ros_node "$@" ;;
  demo)
    shift
    if [[ $# -lt 1 ]]; then echo 'Usage: demo /data/bag [topic]' >&2; exit 2; fi
    bag="$1"
    topic="${2:-/lidar_points}"
    python3 -m metro_guard.ros_node --ros-args -p "input_topic:=$topic" &
    node_pid=$!
    player_pid=''
    cleanup() { kill "$node_pid" ${player_pid:+"$player_pid"} 2>/dev/null || true; }
    trap cleanup EXIT INT TERM
    sleep 2
    ros2 bag play "$bag" --clock --delay 1 --read-ahead-queue-size 2 &
    player_pid=$!
    # Fail fast if either the detector or playback exits unexpectedly.
    wait -n "$node_pid" "$player_pid"
    ;;
  help)
    echo 'Metro Guard: run BAG --output DIR | serve DIR --host 0.0.0.0 | node [--ros-args ...] | demo BAG [TOPIC]'
    ;;
  *) exec "$@" ;;
esac
