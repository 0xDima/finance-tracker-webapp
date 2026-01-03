#!/bin/bash

PORT=8000
PID=$(lsof -ti tcp:$PORT)

if [ -z "$PID" ]; then
  echo "Server is not running on port $PORT"
else
  echo "Stopping server (PID $PID)"
  kill -TERM $PID
fi
