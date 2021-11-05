set PATH=D:\myvenv\Scripts;%PATH%
start python .\business.py
timeout 10
start streamlit run .\user.py --server.maxUploadSize=4096 --server.port 8501
start streamlit run .\manager.py --server.port 8502

