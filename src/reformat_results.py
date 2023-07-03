import ast
import json

import astunparse
import os


class PathVisitor(ast.NodeVisitor):

    def __init__(self, target):
        self.path = ""
        self.tar = target
        self.scope = []
        self.find = False

    def visit(self, node):
        if type(node) == type(self.tar) and node.lineno == self.tar.lineno and node.name == self.tar.name:
            #print("find")
            self.find = True
        if self.find:
            return
        if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)):
            self.scope.append(node.name)
            # print(self.scope)
        if self.find:
            return
        super().visit(node)
        if self.find:
            return
        if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)):
            self.scope.pop()
            # print(self.scope)

    def get_path_in_tree(self, tree):
        self.visit(tree)
        if len(self.scope) < 1:
            return self.tar.name
        else:
            return ".".join(self.scope) + "." + self.tar.name


def generate_results_from_ast(tree):
    res = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            func_id = PathVisitor(node).get_path_in_tree(tree)
            res[func_id] = {}
            res[func_id]["name"] = node.name
            res[func_id]["location"] = node.lineno
            res[func_id]["return"] = []
            res[func_id]["arguments"] = {}
            if node.returns:
                res[func_id]["return"].append(astunparse.unparse(node.returns).replace('\n', ''))
            for arg in node.args.args:
                res[func_id]["arguments"][arg.arg] = []
                if arg.annotation:
                    res[func_id]["arguments"][arg.arg].append(astunparse.unparse(arg.annotation).replace('\n', ''))

    res['global'] = {}

    class VariableVisitor(ast.NodeVisitor):
        def visit_Module(self, tree):
            for node in tree.body:
                if isinstance(node, ast.AnnAssign):
                    var_name = node.target.id
                    var_type = astunparse.unparse(node.annotation).strip()
        # def visit_Assign(self, node):
        #     if isinstance(node.targets[0], ast.Name):
        #         var_name = node.targets[0].id
        #         if isinstance(node.value, ast.AnnAssign):
        #             var_type = astunparse.unparse(node.value.annotation).strip()
                    # print(f"全局变量: {var_name}, 类型: {var_type}")
                    res['global'][var_name] = []
                    res['global'][var_name].append(var_type)

    class ClassVisitor(ast.NodeVisitor):
        def visit_ClassDef(self, node):
            class_name = node.name
            res[class_name] = {}
            for body_item in node.body:
                if isinstance(body_item, ast.AnnAssign):
                    var_name = body_item.target.id
                    var_type = astunparse.unparse(body_item.annotation).strip()
                    # print(f"类 {class_name} 的成员变量: {var_name}, 类型: {var_type}")
                    res[class_name][var_name] = []
                    res[class_name][var_name].append(var_type)

    visitor = VariableVisitor()
    visitor.visit(tree)

    class_visitor = ClassVisitor()
    class_visitor.visit(tree)

    return res


def parse_file(path, type_dict):
    # print(path)
    filename = proj_name + path.replace(dir_path, '').replace('\\', '/').replace('.pyi', '.py')
    if filename in type_dict:
        return
    type_dict[filename] = {}
    try:
        with open(path, encoding='utf-8') as f:
            code = f.read()
        tree = ast.parse(code)
    except:
        print('ERROR: parse file or ast')
        return
    file_dict = generate_results_from_ast(tree)
    type_dict[filename] = file_dict


def parse_directory(path, type_dict):
    for root, dirs, files in os.walk(path):
        for f in files:
            if f.endswith(('.py', '.pyi')):
                parse_file(os.path.join(root, f), type_dict)
        for d in dirs:
            parse_directory(os.path.join(root, d), type_dict)


def normalize_pytype_results(path, output_path):
    proj_dict = {}
    parse_directory(path, proj_dict)
    with open(output_path, 'w') as f:
        json.dump(proj_dict, f, indent=4)


def generate_results_from_type4py_json(d):
    res = {}
    for file in d:
        filename = file.replace(proj_name + '/' + proj_name, proj_name)
        res[filename] = {}
        for func in d[file]['funcs']:
            func_id = func['name']
            res[filename][func_id] = {}
            res[filename][func_id]['name'] = func['name']
            res[filename][func_id]['location'] = func['fn_lc'][0][0]
            res[filename][func_id]['return'] = []
            if 'ret_type_p' in func:
                for rtype in func['ret_type_p']:
                    res[filename][func_id]['return'].append(rtype[0])
            elif 'ret_type' in func:
                res[filename][func_id]['return'].append(func['ret_type'])
            res[filename][func_id]['arguments'] = {}
            if 'params_p' in func:
                for a in func['params_p']:
                    res[filename][func_id]['arguments'][a] = []
                    for atype in func['params_p'][a]:
                        res[filename][func_id]['arguments'][a].append(atype[0])
            elif 'params' in func:
                for a in func['params']:
                    res[filename][func_id]['arguments'][a] =[]
                    for atype in func['params'][a]:
                        res[filename][func_id]['arguments'][a].append(atype[0])
            res[filename][func_id]['variables'] = {}
            if 'variables_p' in func:
                for v in func['variables_p']:
                    res[filename][func_id]['variables'][v] = []
                    for vtype in func['variables_p'][v]:
                        res[filename][func_id]['variables'][v].append(vtype[0])
            elif 'variables' in func:
                for v in func['variables']:
                    res[filename][func_id]['variables'][v] = []
                    for vtype in func['variables'][v]:
                        res[filename][func_id]['variables'][v].append(vtype[0])

        for cls in d[file]['classes']:
            for func in cls['funcs']:
                func_id = cls['name'] + '.' + func['name']
                res[filename][func_id] = {}
                res[filename][func_id]['name'] = func['name']
                res[filename][func_id]['location'] = func['fn_lc'][0][0]
                res[filename][func_id]['return'] = []
                if 'ret_type_p' in func:
                    for rtype in func['ret_type_p']:
                        res[filename][func_id]['return'].append(rtype[0])
                elif 'ret_type' in func:
                    res[filename][func_id]['return'].append(func['ret_type'])
                res[filename][func_id]['arguments'] = {}
                if 'params_p' in func:
                    for a in func['params_p']:
                        res[filename][func_id]['arguments'][a] = []
                        for atype in func['params_p'][a]:
                            res[filename][func_id]['arguments'][a].append(atype[0])
                elif 'params' in func:
                    for a in func['params']:
                        res[filename][func_id]['arguments'][a] = []
                        for atype in func['params'][a]:
                            res[filename][func_id]['arguments'][a].append(atype[0])
                res[filename][func_id]['variables'] = {}
                if 'variables_p' in func:
                    for v in func['variables_p']:
                        res[filename][func_id]['variables'][v] = []
                        for vtype in func['variables_p'][v]:
                            res[filename][func_id]['variables'][v].append(vtype[0])
                elif 'variables' in func:
                    for v in func['variables']:
                        res[filename][func_id]['variables'][v] = []
                        for vtype in func['variables'][v]:
                            res[filename][func_id]['variables'][v].append(vtype[0])

        res[filename]['global'] = {}
        if 'variables_p' in d[file]:
            for v in d[file]['variables_p']:
                res[filename]['global'][v] = []
                for vtype in d[file]['variables_p'][v]:
                    res[filename]['global'][v].append(vtype[0])
        elif 'variables' in d[file]:
            for v in d[file]['variables']:
                res[filename]['global'][v] = []
                for vtype in d[file]['variables'][v]:
                    res[filename]['global'][v].append(vtype[0])
    return res


def generate_results_from_hityper_json(d):
    res = {}
    for file in d:
        # filename = file.replace('project_repo/', '')
        filename = file.replace(proj_name + '/' + proj_name, proj_name)
        res[filename] = {}
        for func in d[file]:
            func_and_class = func.split('@')
            func_id = func_and_class[0]
            if func_and_class[1] != 'global':
                func_id = func_and_class[1] + '.' + func_id
            res[filename][func_id] = {}
            res[filename][func_id]['name'] = func_and_class[0]
            res[filename][func_id]['location'] = -1
            res[filename][func_id]['return'] = []
            res[filename][func_id]['arguments'] = {}
            res[filename][func_id]['variables'] = {}
            for var in d[file][func]:
                if var['category'] == 'arg':
                    arg_name = var['name']
                    res[filename][func_id]['arguments'][arg_name] = list(var['type'])
                elif var['category'] == 'return':
                    if len(res[filename][func_id]['return']) > 0:
                        print('ERROR: more than one return')
                        exit()
                    res[filename][func_id]['return'] = list(var['type'])
                elif var['category'] == 'local':
                    var_name = var['name']
                    res[filename][func_id]['variables'][var_name] = list(var['type'])
        res[filename]['global'] = {}
        if 'global@global' in d:
            for var in d['global@global']:
                if var['type'] != 'local':
                    print('not a global variable?')
                    exit()
                res[filename]['global'][var['name']] = list(var['type'])

    return res


def normalize_type4py_results(path, output_path):
    with open(path) as f:
        raw_dict = json.load(f)
    proj_dict = generate_results_from_type4py_json(raw_dict)
    with open(output_path, 'w') as f:
        json.dump(proj_dict, f, indent=4)


def normalize_hityper_results(path, output_path):
    with open(path) as f:
        raw_dict = json.load(f)
    proj_dict = generate_results_from_hityper_json(raw_dict)
    with open(output_path, 'w') as f:
        json.dump(proj_dict, f, indent=4)


if __name__ == '__main__':

    proj_list = ['fabric-2.5.0', 'requests-2.22.0', 'tornado-5.0.2']

    # Pytype
    for proj_name in proj_list:
        print(proj_name)
        dir_path = 'F:\\ShareFiles\\pytype-outputs-test\\' + proj_name  # TODO: original Pytype results (directory)
        output_path = 'D:\\Dataset\\mydateset\\lookatme\\std\\pytype_' + proj_name + '.json'
        normalize_pytype_results(dir_path, output_path)

    # Type4Py
    for proj_name in proj_list:
        print(proj_name)
        dir_path = 'D:\\Dataset\\mydateset\\lookatme\\raw\\type4py_' + proj_name + '.json'  # TODO: original Type4PY results (.json)
        output_path = 'D:\\Dataset\\mydateset\\lookatme\\std\\type4py_' + proj_name + '.json'
        normalize_type4py_results(dir_path, output_path)

    # HiTyper
    for proj_name in proj_list:
        print(proj_name)
        dir_path = 'D:\\Dataset\\mydateset\\lookatme\\raw\\' + proj_name + '_INFERREDTYPES.json'  # TODO: original HiTyper results (.json)
        output_path = 'D:\\Dataset\\mydateset\\lookatme\\std\\hityper_' + proj_name + '.json'
        normalize_hityper_results(dir_path, output_path)
