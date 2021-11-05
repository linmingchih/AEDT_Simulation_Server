# -*- coding: utf-8 -*-

import os
import time
import json
import streamlit as st
from streamlit_autorefresh import st_autorefresh

queue_dir = 'd:/demo'
count = st_autorefresh(interval=1000)

with open('versions.json') as f:
    versions = json.load(f)


with open('queue.json') as f:
    st.session_state.queue = json.load(f)


def dumpQueue():
    with open('queue.json', 'w') as f:
        json.dump(st.session_state.queue, f)

def loadQueue():
    with open('queue.json') as f:
        st.session_state.queue = json.load(f)  

def addQueue(project_name):
    st.session_state.queue.append(project_name)
    dumpQueue()
    
def deleteQueue(project_name):
    st.session_state.queue.remove(project_name)
    dumpQueue()
             
def submit_up(n):
    if n > 0:
        st.session_state.queue[n], st.session_state.queue[n - 1] = st.session_state.queue[n - 1], st.session_state.queue[n]
    dumpQueue()

def submit_down(n): 
    if n < len(st.session_state.queue) - 1:
        st.session_state.queue[n], st.session_state.queue[n + 1] = st.session_state.queue[n + 1], st.session_state.queue[n]
    dumpQueue()

def submit_top(n):
    st.session_state.queue = [st.session_state.queue.pop(n)] + st.session_state.queue
    dumpQueue()

def submit_bottom(n):
    st.session_state.queue = st.session_state.queue + [st.session_state.queue.pop(n)]
    dumpQueue()

def upload(files):
    pass
            

def delete(n):
    os.remove(os.path.join(queue_dir, st.session_state.queue[n]))
    st.session_state.queue.remove(st.session_state.queue[n])
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
st.subheader('-管理者')

if 'password' not in st.session_state:
    if st.text_input('請輸入密碼:') == 'ansys':
        st.session_state.password = True
else:
    if st.button('登出'):
        del(st.session_state.password)

    with open('simulation_status.log') as f:
        text = f.readlines()
    st.text_area('伺服器狀態', ''.join(text[-3:]), height=50)

#%%-----------------------------------------------------------------------------
    st.subheader('-模擬中')
    if len(getFolders()) == 0:
        st.write('無')

    for folder in getFolders():
        if any([i.endswith('.aedt.lock') for i in os.listdir(folder)]):
            aedt = [os.path.join(folder, i) for i in os.listdir(folder) if i.endswith('.aedt')][0]
            
            with st.expander(os.path.basename(folder)):
                c1, c2, c3, c4 = st.columns(4)

                for root, dirs, files in os.walk(os.path.join(queue_dir, folder)):
                    for file in files:                   
                        if file.endswith(".log"):
                            with open(os.path.join(root, file), encoding='UTF-8') as f:
                                log = f.readlines()

                if st.button('Abort'):
                    version = "AnsysEM21.2"
                    os.environ['PATH'] = versions[version]
                    os.system(f'desktopproxy -abort {aedt}')
                        
                st.text_area('Simulation Message', ''.join(log[-8:]), height=300)

    #%%-----------------------------------------------------------------------------
    st.subheader('-等待模擬專案')
    if len(st.session_state.queue) == 0:
        st.write('無')
        
    for n, i in enumerate(st.session_state.queue):
        with st.expander(os.path.basename(i)):
            c1, c2, c3, c4, c5, c6, c7, c8, c9, c10 = st.columns(10)
            with c1:
                st.button('▲', key=f'move_up_{i}', on_click=submit_up, args=(n,))
            with c2:
                st.button('▼', key=f'move_down_{i}', on_click=submit_down, args=(n,))
            with c3:
                st.button('Top', key=f'move_top_{i}', on_click=submit_top, args=(n,))
            with c4:
                st.button('Bottom', key=f'move_bottom_{i}', on_click=submit_bottom, args=(n,))
            with c8:
                st.button('Delete', key=f'delete_{i}', on_click=delete, args=(n,))

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
            st.download_button('download', data, file)
