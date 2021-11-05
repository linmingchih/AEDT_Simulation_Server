ansysEM_path = "C:/Program Files/AnsysEM"
line_notify_handler = ''
queue_dir = 'D:/demo'
idle_skip_sec = 600
days_to_keep = 3
cores = 20
#line_notify_handler = ''

import os
import time
import json
import requests
import datetime
import shutil
import psutil
import logging
import subprocess
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

os.chdir(os.path.dirname(__file__))
queue_path = os.path.abspath('queue.json')

log_format = '%(asctime)s %(levelname)s: %(message)s'
logging.basicConfig(filename='simulation_status.log', filemode='w', level=logging.DEBUG, format=log_format)
logging.getLogger().addHandler(logging.StreamHandler())
logging.info('Server Started!')

def addQueue(project_name):
    with open(queue_path) as f:
        queue = json.load(f)
    queue.append(project_name)
    with open(queue_path, 'w') as f:
        json.dump(queue, f, indent=4)

def popQueue():
    with open(queue_path) as f:
        queue = json.load(f)
    if queue:
        project_name = queue.pop(0)
        with open(queue_path, 'w') as f:
            json.dump(queue, f, indent=4)
        return project_name
    else:
        None

def initializeVersions():
    result = {}
    for root, dirs, files in os.walk(ansysEM_path):
        for file in files:
            if file == 'ansysedt.exe':
                path = os.path.normpath(root)                
                version = path.split(os.sep)[-2]
                result[version] = path.replace(os.sep, '/')
                
    with open('versions.json', 'w') as f:
        json.dump(result, f, indent=4)
    return result


def inintilizeQueue():
    result = []
    for i in os.listdir(queue_dir):
        x = os.path.join(queue_dir, i)
        if os.path.isdir(x):
            if any([j.endswith('.aedt') for j in os.listdir(x)]):
                result.append(x)
            else:
                shutil.rmtree(x)                
        elif i.endswith('.aedtz'):
            result.append(x)
        elif i.endswith('.zip'):
            pass
        else:
            os.remove(x)

    with open(queue_path, 'w') as f:
        json.dump(result, f, indent=4)

def deleteZipFileOverDays():
    for dirpath, dirnames, filenames in os.walk(queue_dir):
        for file in filenames:
            if file.endswith('.zip'):
                curpath = os.path.join(dirpath, file)
                file_modified = datetime.datetime.fromtimestamp(os.path.getmtime(curpath))
                if datetime.datetime.now() - file_modified > datetime.timedelta(days=days_to_keep):
                    os.remove(curpath)

def lineNotifyMessage(msg):
    if 'line_notify_handler' in locals():
        headers = {
            "Authorization": "Bearer " + line_notify_handler, 
            "Content-Type" : "application/x-www-form-urlencoded"
        }
        
        payload = {'message': msg}
        r = requests.post("https://notify-api.line.me/api/notify", headers = headers, params = payload)
        return r.status_code


class MyHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.src_path.endswith('.aedt') or event.src_path.endswith('.zip'):
            logging.info(f'{event.src_path} is created')
    
    def on_deleted(self, event):
        pass


class project():
    def __init__(self, project_path):
        os.chdir(queue_dir)
        if project_path.endswith('.aedtz'):            
            new_folder_name = os.path.basename(project_path)[:-6]
            self.folder = os.path.join(queue_dir, new_folder_name)
            os.mkdir(self.folder)
            
            self.target = os.path.join(self.folder, os.path.basename(project_path))
            shutil.move(project_path, self.target)
            os.chdir(self.folder)
        else:
            self.folder = project_path
            for file in os.listdir(project_path):
                if file.endswith('.aedt'):
                    self.target = os.path.join(self.folder, file)
                    break                
    
    def run(self):
        idle_time = 0
        version = os.path.basename(self.folder).split('_')[0]
        os.chdir(queue_dir)
        os.environ['PATH'] = versions[version]
        p = subprocess.Popen(['ansysedt', 
                              '-BatchSolve', 
                              '-ng', 
                              '-monitor', 
                              '-autoextract', 
                              'reports', 
                              '-machinelist', 
                              'list="localhost:4:{}:90%:1"'.format(cores), 
                              self.target.replace('\\','/')])
        last_size = 0
        while(p.poll() == None):
            logging.info(f'process code: {p.poll()}')
            process = psutil.Process(p.pid)
            size_m = process.memory_info().rss
            logging.info(f'memory size: {size_m}, idle: {idle_time} secs')
            time.sleep(10)
     
            if size_m != last_size:
                last_size = size_m
                idle_time = 0
            else:
                idle_time += 10
            
            if idle_time > idle_skip_sec:
                p.terminate()
                time.sleep(1)
                for f in os.listdir(self.folder):
                    if f.endswith('.lock'):
                        os.remove(os.path.join(self.folder, f))
                return -1
        
        return p.poll()
                        
    def archive(self):
        os.chdir(queue_dir)
        shutil.make_archive(self.folder, 'zip', self.folder)

        time.sleep(1)
        shutil.rmtree(self.folder)
        
if __name__ == '__main__':
    versions = initializeVersions()
    inintilizeQueue()
    
    event_handler = MyHandler()
    observer = Observer()
    observer.schedule(event_handler, path=queue_dir, recursive=True)
    observer.start()
    
    try:
        while True:
            deleteZipFileOverDays()
            
            if 'prj' not in locals():
                todo_prj_name = popQueue()
                now = str(datetime.datetime.now())[:-7]
                logging.info(f'{now} waitting')
                time.sleep(10)
                
                if todo_prj_name:
                    logging.info('-'*80)                    
                    logging.info('start: {}!'.format(todo_prj_name))
                    prj = project(todo_prj_name)
                    pcode = prj.run()
                    
                    if pcode == 0:
                        logging.info('{} accomplished!'.format(todo_prj_name))
                        lineNotifyMessage(f'{todo_prj_name} is Accomplished!')
                        prj.archive()
                        del(prj)                        
                    
                    elif pcode == -1:
                        logging.info('{} no response!'.format(todo_prj_name))
                        lineNotifyMessage(f'{todo_prj_name} no response!')
                        prj.archive()
                        del(prj)                        
                    
                    elif pcode == 103:
                        logging.info('{} interrupted!'.format(todo_prj_name))
                        lineNotifyMessage(f'{todo_prj_name} interrupted!')
                        addQueue(os.path.basename(todo_prj_name)[:-6])
                        del(prj)
                        
                    else:
                        logging.info('{} failed!'.format(todo_prj_name))
                        lineNotifyMessage(f'{todo_prj_name} failed!')
                        prj.archive()
                        del(prj)                                              
    except:
        lineNotifyMessage('Simulation Server Terminated')
        logging.exception('ERROR')
    
    observer.join()
