#!/bin/bash
# Start React frontend without ESLint
echo "🚀 Starting HarakaCare Frontend (No ESLint)"
cd /home/medisoft/Desktop/harakacare/frontend
export ESLINT_NO_DEV_ERRORS=true
export GENERATE_SOURCEMAP=false
export TSC_COMPILE_ON_ERROR=true
npm start
