@echo off
echo ===================================================
echo   CoolOPS Firebase ^& Cloud Run Dağıtım Yardımcısı
echo ===================================================
echo.
echo Bu betik, uygulamanızı Google Cloud Run ve Firebase Hosting'e dağıtır.
echo Başlamadan önce Google Cloud SDK (gcloud) ve Firebase CLI (firebase-tools)
echo bilgisayarınızda kurulu olmalıdır.
echo.

set /p PROJECT_ID="Firebase Proje ID girin (Varsayılan: coolops-bf6a0): "
if "%PROJECT_ID%"=="" set PROJECT_ID=coolops-bf6a0

echo.
echo [1/5] Firebase oturumu açılıyor...
call firebase login

echo.
echo [2/5] Google Cloud kimlik doğrulaması yapılıyor...
call gcloud auth login
call gcloud config set project %PROJECT_ID%
call gcloud auth configure-docker

echo.
echo [3/5] Docker imajı oluşturuluyor ve Google Cloud Builds ile yükleniyor...
call gcloud builds submit --tag gcr.io/%PROJECT_ID%/cool-ops-app

echo.
echo [4/5] Google Cloud Run servisi dağıtılıyor...
call gcloud run deploy cool-ops-app --image gcr.io/%PROJECT_ID%/cool-ops-app --platform managed --allow-unauthenticated --region us-central1

echo.
echo [5/5] Firebase Hosting yönlendirmeleri dağıtiliyor...
call firebase deploy --only hosting --project %PROJECT_ID%

echo.
echo ===================================================
echo Dağıtım tamamlandı! Uygulamanız Firebase üzerinde aktif.
echo ===================================================
pause
