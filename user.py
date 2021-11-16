# -*- coding: utf-8 -*-

import os
import time
import json
import streamlit as st
from streamlit_autorefresh import st_autorefresh

queue_dir = 'd:/demo'
count = st_autorefresh(interval=10000)

with open('versions.json') as f:
    versions = json.load(f)


with open('queue.json') as f:
    st.session_state.queue = json.load(f)


def dumpQueue():
    with open('queue.json', 'w') as f:
        json.dump(st.session_state.queue, f)

def addQueue(project_name):
    st.session_state.queue.append(project_name)
    dumpQueue()

def getFolders():
    folders = [os.path.join(queue_dir, i) for i in os.listdir(queue_dir) if os.path.isdir(os.path.join(queue_dir, i))]
    return folders

def getExt(ext = 'aedtz'):
    files = [i for i in os.listdir(queue_dir) if i.endswith(ext)]
    files.sort(key=lambda x: os.path.getmtime(os.path.join(queue_dir, x)))
    return files


#%%-----------------------------------------------------------------------------
st.title('AEDT 遠端模擬平台 v2021.11')

#%%-----------------------------------------------------------------------------
st.subheader('-提交專案(.aedtz)')

with st.form(key='my_form', clear_on_submit=True):
    version = st.selectbox('ANSYS EM 版本', list(versions)[::-1])
    
    files = [] 
    for file in st.file_uploader("上傳 .aedtz", accept_multiple_files=True, type='aedtz'):
        if file not in files:
            files.append(file)

    if st.form_submit_button(label='提交'):
        for file in files:
            project_path = os.path.join(queue_dir, f'{version}_{file.name}')                  
            with open(project_path, 'wb') as f:
                f.write(file.getbuffer())
                
            addQueue(f'{version}_{file.name}')
#%%-----------------------------------------------------------------------------
st.subheader('-模擬中')
if len(getFolders()) == 0:
    st.write('無')

for folder in getFolders():
    if any([i.endswith('.aedt.lock') for i in os.listdir(folder)]):
        with st.expander(os.path.basename(folder)):
            c1, c2, c3, c4 = st.columns(4)
            with c4:
                st.button('Refresh Status')
                for root, dirs, files in os.walk(os.path.join(queue_dir, folder)):
                    for file in files:                   
                        if file.endswith(".log"):
                            with open(os.path.join(root, file), encoding='UTF-8') as f:
                                log = f.readlines()

            st.text_area('Simulation Message', ''.join(log[-8:]), height=300)



#%%-----------------------------------------------------------------------------
st.subheader('-等待模擬專案')
if len(st.session_state.queue) == 0:
    st.write('無')
    
for n, i in enumerate(st.session_state.queue):
    with st.expander(os.path.basename(i)):
        pass

#%%-----------------------------------------------------------------------------
st.subheader('-已完成模擬專案')

if len(getExt('zip')) == 0:
    st.write('無')
    
for file in getExt('zip')[::-1]:
    file_path = os.path.join(queue_dir, file)
    file_size = round(os.path.getsize(file_path)/1e6, 1)
    file_date = time.ctime(os.path.getmtime(file_path))
    with st.expander('{}'.format(file)):
        with open(os.path.join(queue_dir, file), 'rb') as f:
            data = f.read()
        st.write('{}MB, {}'.format(file_size, file_date))            
        st.download_button('下載', data, file)
