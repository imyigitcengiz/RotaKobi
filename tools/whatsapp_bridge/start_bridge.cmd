@echo off
chcp 65001 >nul
title GY WhatsApp Bridge
cd /d "C:\Users\Admin\İndirilenler\KobiOPS\tools\whatsapp_bridge"
echo [%date% %time%] Köprü baslatiliyor...
echo Node: "C:\Program Files\nodejs\node.exe"
"C:\Program Files\nodejs\node.exe" server.js
if errorlevel 1 (
  echo.
  echo HATA: Köprü kapandi. Yukaridaki kirmizi mesaji okuyun.
  echo node_modules yoksa: npm install
  pause
)
