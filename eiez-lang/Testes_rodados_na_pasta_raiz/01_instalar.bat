@echo off
echo ============================================
echo  EIEZ/ZIE — Instalando dependencias
echo ============================================
echo.

pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install pandas numpy scikit-learn matplotlib codecarbon yfinance

echo.
echo ============================================
echo  Instalacao concluida!
echo  Agora rode: python 02_experimento.py
echo ============================================
pause
