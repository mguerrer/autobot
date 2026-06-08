#!/bin/bash
while true; do
  echo "[$(date)] Iniciando WA Bridge..."
  node index.js
  EXIT_CODE=$?
  echo "[$(date)] WA Bridge terminó con código $EXIT_CODE. Reiniciando en 3s..."
  sleep 3
done