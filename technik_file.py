import psutil



def process_analysis():
    sp_prosess = []
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            sp_prosess.append((proc.info['pid'], proc.info['name']))
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return sp_prosess

def kill_process(kill_name):
    sp = process_analysis()
    for pid, name in sp:
        if name.lower() == kill_name.lower():
            p = psutil.Process(pid)
            p.kill()


kill_process("Paint.exe")
print(process_analysis())
