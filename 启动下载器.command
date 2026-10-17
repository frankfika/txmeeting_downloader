#!/bin/bash
cd -- "$(dirname -- "$0")"
./start.sh
result=$?
echo ""
read -r -p "按回车关闭窗口…"
exit "$result"
