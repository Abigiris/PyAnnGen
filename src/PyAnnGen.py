import os
import json
import copy
import sys

class TypeCategory:
    Elementary = 'Elementary'
    Parametric = 'Parametric'
    Union = 'Union'
    Dynamic = 'Dynamic'
    Variable = 'Variable'
    UserDefined = 'UserDefined'


ElementaryType = ('int', 'float', 'bool', 'str', 'bytes', 'None')
ParametricType = ('list', 'tuple', 'dict', 'set', 'callable', 'generator')


def classify_a_type(t):
    # print(dir(__builtins__))
    def preprocess(t):
        std_t = t.replace('"', '').replace("'", "")
        std_t = std_t.replace('builtin.', '').replace('typing.', '')
        return std_t
    if t in ('Any', 'typing.Any', 't.Any'):
        return TypeCategory.Dynamic
    if t.startswith('_T'):
        return TypeCategory.Variable
    if t.startswith(('Union', 'Optional', 'typing.Union', 'typing.Optional', 't.Union', 't.Optional')):
        return TypeCategory.Union
    if t.startswith('builtins.'):
        t = t.split('.', maxsplit=1)[1]
    if t in dir(__builtins__) and t not in ParametricType:
        return TypeCategory.Elementary
    if '[' in t or t.lower() in ParametricType:
        return TypeCategory.Parametric
    return TypeCategory.UserDefined


def revise_pytype_filepath(pytype_dict, type4py_dict, hityper_dict):
    exist_files = set(type4py_dict).union(hityper_dict)
    d = {}
    for raw_filename in pytype_dict:
        py_filename = raw_filename.replace('pyi/', '')
        if py_filename in exist_files:
            d[py_filename] = dict(pytype_dict[raw_filename])
            continue
        base_filename = '/' + py_filename.split('/')[-1]
        may_filenames = []
        for exist_filename in exist_files:
            if exist_filename.endswith(base_filename):
                may_filenames.append(exist_filename)
        if len(may_filenames) == 1:
            d[may_filenames[0]] = dict(pytype_dict[raw_filename])
        else:
            d[py_filename] = dict(pytype_dict[raw_filename])
    for filename in d:
        for func_id in d[filename]:
            if 'return' in d[filename][func_id]:
                d[filename][func_id]['variables'] = {}

    return d


def parse_point(pytype_list, type4py_list, hityper_list):

    if len(pytype_list) > 0 and classify_a_type(pytype_list[0]) in (TypeCategory.Elementary, TypeCategory.Parametric, TypeCategory.Union, TypeCategory.UserDefined):
        return list(pytype_list)

    def parse_type_variable(type_str):
        s = type_str.strip("'").strip('"')
        if s.startswith('_T') and len(s) > 3 and '.' not in s and '[' not in s:
            return s.lstrip('_T')
        else:
            return type_str

    if len(pytype_list) > 0 and classify_a_type(pytype_list[0]) == TypeCategory.Variable:
        tl = []
        tl.append(parse_type_variable(pytype_list[0]))
        return tl

    if len(type4py_list) > 0 and len(hityper_list) == 0:
        return list(type4py_list)
    if len(type4py_list) == 0 and len(hityper_list) > 0:
        return list(hityper_list)

    if len(type4py_list) > 0 and len(hityper_list) > 0:
        ranks = {}
        for t in type4py_list:
            if t not in ranks:
                ranks[t] = 0
            ranks[t] += (1 / (type4py_list.index(t) + 1) / len(type4py_list))
        for t in hityper_list:
            if t not in ranks:
                ranks[t] = 0
            ranks[t] += (1 / (hityper_list.index(t) + 1) / len(hityper_list))
        ann_dict = sorted(ranks.items(), key=lambda x: x[1], reverse=True)
        ann_list = []
        for k in ann_dict:
            ann_list.append(k[0])
        return ann_list
    return []


def parse_project(pytype_dict, type4py_dict, hityper_dict):
    pytype_dict = revise_pytype_filepath(pytype_dict, type4py_dict, hityper_dict)
    all_files = set(pytype_dict.keys()).union(type4py_dict.keys(), hityper_dict.keys())
    res = {filename: {} for filename in all_files}
    for filename in res:
        if filename in type4py_dict:
            res[filename] = copy.deepcopy(type4py_dict[filename])
        elif filename in hityper_dict:
            res[filename] = copy.deepcopy(hityper_dict[filename])
        else:
            res[filename] = copy.deepcopy(pytype_dict[filename])

        def is_exist(res_dict, filename, func_id, category=None, name=None):
            if not category:
                return filename in res_dict and func_id in res_dict[filename]
            else:
                return filename in res_dict and func_id in res_dict[filename] and name in res_dict[filename][func_id][category]

        for func_id in res[filename]:
            if 'return' in res[filename][func_id]:
                p = pytype_dict[filename][func_id]['return'] if is_exist(pytype_dict, filename, func_id) else []
                t = type4py_dict[filename][func_id]['return'] if is_exist(type4py_dict, filename, func_id) else []
                h = hityper_dict[filename][func_id]['return'] if is_exist(hityper_dict, filename, func_id) else []
                res[filename][func_id]['return'] = parse_point(p, t, h)
                for arg in res[filename][func_id]['arguments']:
                    p = pytype_dict[filename][func_id]['arguments'][arg] if is_exist(pytype_dict, filename, func_id, 'arguments', arg) else []
                    t = type4py_dict[filename][func_id]['arguments'][arg] if is_exist(type4py_dict, filename, func_id, 'arguments', arg) else []
                    h = hityper_dict[filename][func_id]['arguments'][arg] if is_exist(hityper_dict, filename, func_id, 'arguments', arg) else []
                    res[filename][func_id]['arguments'][arg] = parse_point(p, t, h)
                if 'variables' not in res[filename][func_id]:
                    res[filename][func_id]['variables'] = {}
                    continue
                for var in res[filename][func_id]['variables']:
                    p = pytype_dict[filename][func_id]['variables'][var] if is_exist(pytype_dict, filename, func_id, 'variables', var) else []
                    t = type4py_dict[filename][func_id]['variables'][var] if is_exist(type4py_dict, filename, func_id, 'variables', var) else []
                    h = hityper_dict[filename][func_id]['variables'][var] if is_exist(hityper_dict, filename, func_id, 'variables', var) else []
                    res[filename][func_id]['variables'][var] = parse_point(p, t, h)
            else:
                scope_name = func_id
                for var in res[filename][func_id]:
                    p = pytype_dict[filename][scope_name][var] if is_exist(pytype_dict, filename, scope_name) \
                                                                and var in pytype_dict[filename][scope_name] else []
                    t = type4py_dict[filename][scope_name][var] if is_exist(type4py_dict, filename, scope_name) \
                                                                 and var in type4py_dict[filename][scope_name] else []
                    h = hityper_dict[filename][scope_name][var] if is_exist(hityper_dict, filename, scope_name) \
                                                                 and var in hityper_dict[filename][scope_name] else []
                    res[filename][scope_name][var] = parse_point(p, t, h)

        if 'global' not in res[filename]:
            res[filename]['global'] = {}

    return res


if __name__ == '__main__':
    proj_list = ['fabric-2.5.0', 'requests-2.22.0', 'tornado-5.0.2']
    for proj_name in proj_list:
        with open('D:\\Dataset\\mydateset\\lookatme\\std\\pytype_' + proj_name + '.json') as f:  # TODO: results of reformatting
            pytype_dict = json.load(f)
        with open('D:\\Dataset\\mydateset\\lookatme\\std\\type4py_' + proj_name + '.json') as f:
            type4py_dict = json.load(f)
        with open('D:\\Dataset\\mydateset\\lookatme\\std\\hityper_' + proj_name + '.json') as f:
            hityper_dict = json.load(f)
        res = parse_project(pytype_dict, type4py_dict, hityper_dict)
        with open('D:\\Dataset\\mydateset\\lookatme\\std\\types_' + proj_name + '.json', 'w') as f:  # TODO: FINAL results
            json.dump(res, f, indent=4)