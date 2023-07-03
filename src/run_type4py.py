import json
import os


import requests


class Type4PyTypeCollector:
    type_dict: dict
    ann_points: int
    unload_files: int
    load_files: int

    def __init__(self):
        self.type_dict = {}
        self.ann_points = 0
        self.unload_files = 0
        self.load_files = 0

    def get_raw_data(self, filepath):
        if not filepath.startswith('D:\\Dataset\\'):
            return
        if '.venv\\' in filepath:
            print('Pass: ' + filepath)
            return
        # with open(filepath, 'r', encoding='utf-8') as f:
        #     r = requests.post("https://type4py.com/api/predict?tc=0", f.read(), verify=False)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                r = requests.post("https://type4py.com/api/predict?tc=0", f.read(), verify=False)
            print("SUCCESS: " + filepath)
        except:
            self.unload_files += 1
            print("ERROR: cannot upload file " + filepath)
            return
        try:
            filename = filepath.replace(dir_path, "")
            filename = filename.replace("\\", "/")
            if not r.json()['error']:
                self.load_files += 1
                self.type_dict[filename] = r.json()['response']
        except:
            print("???")
            return

    def parse_directory(self, root):
        if not root.startswith('D:\\Dataset\\'):
            return
        for root, dirs, files in os.walk(root):
            for f in files:
                path = os.path.join(root, f)
                if path.endswith('.py'):
                    # self.parse_file(path)
                    self.get_raw_data(path)
            for d in dirs:
                self.parse_directory(d)


if __name__ == '__main__':
    dir_path = "D:\\Dataset\\mydateset\\some_projects\\"
    # proj_list = os.listdir(dir_path)
    proj_list = ['fabric-2.5.0', 'requests-2.22.0', 'tornado-5.0.2']
    for proj_name in proj_list:
        proj_path = dir_path + proj_name  # TODO: source code (project directory)
        print('======= ' + proj_name + ' ========')
        output_path = "D:\\Dataset\\mydateset\\lookatme\\raw\\type4py_" + proj_name + ".json"  # TODO: Type4Py results
        collector = Type4PyTypeCollector()
        collector.parse_directory(proj_path)
        print(proj_name + ": load " + str(collector.load_files) + " files, unload " + str(
            collector.unload_files) + " files")
        with open(output_path, "w") as f:
            json.dump(collector.type_dict, f, indent=4)
