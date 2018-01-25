from operator import itemgetter
from urllib import request

import simplejson
import codecs
import sys
import os
import re

_headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.90 Safari/537.36',
    'Content-Type': 'text/html;charset=UTF-8'
}
_argument_priority = [1, 2, 2, 3, 4, 4, 5]
_arguments = {
    '-in_path': _argument_priority[0], '-I': _argument_priority[0],
    '-gen_area_code': _argument_priority[1], '-G': _argument_priority[1],
    '-set_area_code': _argument_priority[2], '-S': _argument_priority[2],
    '-add_sku_id': _argument_priority[3], '-A': _argument_priority[3],
    '-out_path': _argument_priority[4], '-O': _argument_priority[4],
    '-not_output_file': _argument_priority[5], '-N': _argument_priority[5],
    '-remove_sku_id': _argument_priority[6], '-R': _argument_priority[6]
}
_area_code = '16_1315_1316_53522'
_out_path = './out.txt'
_in_path = './in.txt'
_sku_info = {}
_sku_ids = {}

_double_byte_rule = re.compile('<strong>([\u4e00-\u9fa5]+)</strong>|(\d+)')
_product_rule = re.compile('<div class=\"p-name\">([^<]*)</div>')
_sku_ids_rule = re.compile('https://item.jd.com/(\d+)')
_value_behind_equality_sign_rule = re.compile('=(.*)')
_argument_rule = re.compile('(-[_A-Za-z0-9]+)')
_alpha_rule = re.compile('([a-zA-Z]+)')


def get_html_encoding(headers):
    if headers is None or headers['Content-Type'] is None:
        return 'gb18030'
    encoding = get_value_behind_equality_sign(headers['Content-Type'])
    if encoding is None:
        return 'gb18030'
    if -1 != encoding.find('gb'):
        encoding = 'gb18030'
    return encoding


def get_html_content(url):
    global _headers
    req = request.Request(url=url, headers=_headers)
    page = request.urlopen(req)
    encoding = get_html_encoding(page.headers)
    str_list = page.readlines()
    contents = ""
    for string in str_list:
        contents += string.decode(encoding)
    return contents


def check_redirect(url):
    global _headers
    req = request.Request(url=url, headers=_headers)
    page = request.urlopen(req)
    return page.url != url


def regex_result(regex, string, find_all=False, separator=' '):
    result = ''
    if find_all:
        result_list = regex.findall(string)
        if result_list is None:
            return None
        for t in result_list:
            for s in t:
                if s != '':
                    result += s + separator
    else:
        result_match = regex.search(string)
        if result_match is None:
            return None
        for s in result_match.groups():
            if s is not None and s != '':
                result += s + separator
    if result == '':
        return None
    elif separator == '':
        return result.strip()
    else:
        return result[0:-len(separator)].strip()


def check_sku_id(sku_id):
    url = 'https://item.jd.com/' + sku_id + '.html'
    return not check_redirect(url)


def get_sku_id(url):
    global _sku_ids_rule
    return regex_result(_sku_ids_rule, url)


def get_argument_option(string):
    global _argument_rule
    return regex_result(_argument_rule, string)


def get_value_behind_equality_sign(string):
    global _value_behind_equality_sign_rule
    return regex_result(_value_behind_equality_sign_rule, string)


def get_product_name(sku_id):
    url = 'https://item.jd.com/' + sku_id + '.html'
    contents = get_html_content(url)
    global _product_rule
    return regex_result(_product_rule, contents)


def get_param_value_in_url(url, param):
    rule = re.compile('(?<=' + param + '=)(\d+)')
    return regex_result(rule, url)


def get_product_price(sku_id):
    url = 'http://p.3.cn/prices/mgets?skuIds=' + sku_id
    json_resp = get_html_content(url)
    json_obj = simplejson.loads(json_resp)
    if len(json_obj) == 0 or 'p' not in json_obj[0]:
        return ''
    return json_obj[0]['p']


def get_product_stock(sku_id, area_code):
    url = 'https://c0.3.cn/stock?skuId=' + sku_id + '&area=' + area_code + '&cat=1,2,3&extraParam={"originid":"1"}'
    json_resp = get_html_content(url)
    json_obj = simplejson.loads(json_resp)
    if 'stock' not in json_obj or 'stockDesc' not in json_obj['stock']:
        return ''
    global _double_byte_rule
    return regex_result(_double_byte_rule, json_obj['stock']['stockDesc'], True, ':')


def get_product_coupon(sku_id, area_code):
    url = 'https://cd.jd.com/promotion/v2?skuId=' + sku_id + '&area=' + area_code + '&cat=1,2,3'
    json_resp = get_html_content(url)
    json_obj = simplejson.loads(json_resp)
    if 'skuCoupon' not in json_obj or len(json_obj['skuCoupon']) == 0:
        return ''
    coupon_list = json_obj['skuCoupon']
    result = ''
    for info in coupon_list:
        result += str(info['quota']) + '-' + str(info['discount']) + ', '
    return result[:-2]


def get_length(string):
    length = len(string)
    utf8_length = len(string.encode('utf-8'))
    return ((utf8_length - length) >> 1) + length


# align_type -1: left, 0: center, 1: right
def align_string(string, width, align_type=1, fill_char=' '):
    length = get_length(string)
    if width <= length:
        return string
    if align_type == -1:
        front = 0
    elif align_type == 0:
        front = (width - length) >> 1
    else:
        front = width - length

    front_space = ''
    for idx in range(0, front):
        front_space += fill_char
    behind = width - length - front
    behind_space = ''
    for idx in range(0, behind):
        behind_space += fill_char
    return front_space + string + behind_space


def get_area_code_info(area_id):
    url = 'https://d.jd.com/area/get?fid=' + area_id
    json_resp = get_html_content(url)
    json_obj = simplejson.loads(json_resp)
    if len(json_obj) == 0:
        return None
    return json_obj


def get_area_id_name(area_id, parent_area_id=None):
    if parent_area_id is not None:
        json_obj = get_area_code_info(parent_area_id)
        int_area_id = int(area_id)
        if len(json_obj) == 0:
            return None
        for obj in json_obj:
            if 'id' not in obj or 'name' not in obj:
                continue
            if int_area_id == obj['id']:
                return obj['name']
        return None


def check_area_code(area_code):
    area_ids = area_code.split('_')
    length = len(area_ids)
    if length < 2:
        return None
    area_code_info = ''
    area_id_name = get_area_id_name(area_ids[0], '0')
    if area_id_name is None:
        return None
    area_code_info += area_id_name
    for idx in range(0, length - 1):
        area_id_name = get_area_id_name(area_ids[idx + 1], area_ids[idx])
        if area_id_name is None:
            return None
        area_code_info += '_' + area_id_name
    return area_code_info


def read_sku_ids_in_file(file_path):
    contents = read_file(file_path, 'utf-8', True, True)
    if contents is None:
        return False
    global _sku_ids
    for line in contents:
        sku_id = get_sku_id(line)
        if sku_id is not None and check_sku_id(sku_id):
            _sku_ids[sku_id] = True


def store_sku_id(new_sku_ids):
    global _in_path, _sku_ids
    if not _sku_ids:
        read_sku_ids_in_file(_in_path)
    need_store = []
    result = True
    for sku_id in new_sku_ids:
        if sku_id is None or len(sku_id) == 0:
            print('sku_id 不能为空.')
            result = False
        if check_sku_id(sku_id):
            print('sku_id:', sku_id, '错误')
            result = False
        if sku_id not in _sku_ids:
            need_store.append(sku_id)
    if len(need_store) == 0:
        return result
    with codecs.open(_in_path, 'w+', 'utf-8') as fp:
        for sku_id in need_store:
            fp.write(os.linesep + 'https://item.jd.com/' + sku_id + '.html' + os.linesep)
    return result


def check_file(file_path, check_writable=False, create_while_no_exist=False):
    result = True
    if not os.access(file_path, os.R_OK):
        result = False
    if result and check_writable and not os.access(file_path, os.W_OK):
        return False
    if not result and create_while_no_exist:
        fp = open(file_path, 'a')
        fp.close()
        result = True
    return result


def read_file(file_path, encoding='utf-8', check_writable=False, create_while_no_exist=False):
    if not check_file(file_path, check_writable, create_while_no_exist):
        return None
    with codecs.open(file_path, 'r', encoding) as fp:
        contents = fp.readlines()
    return contents


def get_info_in_file():
    global _area_code, _sku_ids, _in_path
    contents = read_file(_in_path)
    if contents is None:
        return
    for string in contents:
        sku_id = get_sku_id(string)
        if sku_id is not None:
            _sku_ids[sku_id] = True
        else:
            area_code_tmp = get_value_behind_equality_sign(string)
            if area_code_tmp is not None:
                _area_code = area_code_tmp


def get_argument_priority(arg_key):
    global _arguments
    if arg_key in _arguments:
        return _arguments[arg_key]
    return -1


def handle_in_path(arg_value):
    result = check_file(arg_value, True)
    if result:
        global _in_path
        _in_path = arg_value
    else:
        print('-in_path failure.')
    return result


def store_area_code():
    global _area_code, _in_path
    # 不管需不需要写入，都检查是否可以写入
    contents = read_file(_in_path, 'utf-8', True, True)
    if contents is None:
        return False
    tmp_area_code = None
    for idx in range(0, len(contents)):
        if -1 != contents[idx].find('area_code='):
            tmp_area_code = get_value_behind_equality_sign(contents[idx])
            if tmp_area_code is not None and tmp_area_code != _area_code:
                contents[idx] = 'area_code=' + _area_code + os.linesep
            break
    if tmp_area_code is not None:
        if contents[-1][-1] != '\n':
            contents[-1] += '\n'
        contents.append('area_code=' + _area_code + os.linesep)
    with codecs.open(_in_path, 'w', 'utf-8') as fp:
        fp.writelines(contents)
    return True


# 参数只是占位置用的
def generate_area_code(arg_value=None):
    global _area_code, _alpha_rule
    gen_area_code = ''
    area_name = ''
    cur_area_id = '0'
    while True:
        json_obj = get_area_code_info(cur_area_id)
        if json_obj is None:
            gen_area_code = gen_area_code[0:-1]
            _area_code = gen_area_code
            area_name = area_name[0:-1]
            print('当前的区域为,' + area_name, '区域代码为:', _area_code)
            break
        print('输入如果含有 skip 则跳过.')
        for obj in json_obj:
            if 'id' not in obj or 'name' not in obj:
                continue
            # 暂且虑掉国外
            if regex_result(_alpha_rule, obj['name']) is not None:
                continue
            print('name: ' + obj['name'] + ', id: ' + str(obj['id']))
        area_id = input('请选择所在区域: ')
        if area_id.find('skip') != -1:
            print('已结束该命令.')
            return False
        int_area_id = int(area_id)
        for obj in json_obj:
            if int_area_id == obj['id']:
                gen_area_code += area_id + '_'
                area_name += obj['name'] + '-'
                cur_area_id = area_id
                break
    print('存储到 in_path : ' + str(store_area_code()))
    return True


def set_area_code(arg_value):
    result = check_area_code(arg_value)
    if result:
        print('存储到 in_path : ' + str(store_area_code()))
    return result


def add_sku_id(arg_value):
    global _sku_ids
    sku_id_list = arg_value.split(',')
    result = True
    sku_ids_store = []
    for sku_id in sku_id_list:
        if check_sku_id(sku_id) is False:
            print('添加 sku_id :', sku_id, '失败.')
            result = False
            continue
        sku_ids_store.append(sku_id)
    if not store_sku_id(sku_ids_store):
        result = False
    return result


# 参数只是占位置用的
def remove_out_path(arg_value):
    global _out_path
    _out_path = None
    return True


def set_out_path(arg_value):
    if arg_value is None or len(arg_value):
        print(arg_value, '不能为空.')
        return False
    if not check_file(arg_value, True):
        print('文件', arg_value, '不存在或者不可读.')
        return False
    global _out_path
    _out_path = arg_value
    return True


def remove_sku_id(arg_value):
    if arg_value is None or len(arg_value) == 0:
        return False
    global _sku_ids, _in_path
    if not _sku_ids:
        read_sku_ids_in_file(_in_path)
    result = True
    sku_ids = {}
    if arg_value.find('all') != -1:
        sku_ids = _sku_ids
    else:
        for sku_id in arg_value:
            if sku_id in _sku_ids:
                sku_ids[sku_id] = True
            else:
                print(sku_id, '未找到.')
                result = False
    contents = read_file(_in_path, check_writable=True)
    if contents is None:
        print(_in_path, '文件不存在或者不可写.')
        result = False
    new_contents = []
    for line in contents:
        sku_id = get_sku_id(line)
        if sku_id is not None and sku_id in sku_ids:
            continue
        new_contents.append(line)
    with codecs.open(_in_path, 'w', 'utf-8') as fp:
        fp.writelines(new_contents)
    return result


_argument_option = {
    '-in_path': handle_in_path, '-I': handle_in_path,
    '-gen_area_code': generate_area_code, '-G': generate_area_code,
    '-set_area_code': set_area_code, '-S': set_area_code,
    '-add_sku_id': add_sku_id, '-A': add_sku_id,
    '-out_path': set_out_path, '-O': set_out_path,
    '-not_output_file': remove_out_path, '-N': remove_out_path,
    '-remove_sku_id': remove_sku_id, '-R': remove_sku_id,
}


def handle_argv():
    option_result = True
    argv = sys.argv[1:]
    arg_list = []
    for arg_cmd in argv:
        arg_option = get_argument_option(arg_cmd)
        if arg_option is None:
            continue
        arg_priority = get_argument_priority(arg_option)
        if arg_priority == -1:
            continue
        arg_value = get_value_behind_equality_sign(arg_cmd)
        arg_list.append({
            'priority': arg_priority,
            'option': arg_option,
            'value': arg_value
        })
    global _argument_option
    for argument in sorted(arg_list, key=lambda arg: arg['priority']):
        if not _argument_option[argument['option']](argument['value']):
            option_result = False
    return option_result


def generate_sku_info():
    global _sku_info
    for sku_id in _sku_ids:
        _sku_info[sku_id] = {
            'price': get_product_price(sku_id),
            'stock': get_product_stock(sku_id, _area_code),
            'coupon': get_product_coupon(sku_id, _area_code),
            'name': get_product_name(sku_id)
        }


def show_sku_info():
    global _sku_ids, _sku_info
    max_width = {'price': 0, 'stock': 0, 'coupon': 0, 'name': 0}
    for sku_id in _sku_ids:
        max_width['price'] = max(max_width['price'], get_length(_sku_info[sku_id]['price']))
        max_width['stock'] = max(max_width['stock'], get_length(_sku_info[sku_id]['stock']))
        max_width['coupon'] = max(max_width['coupon'], get_length(_sku_info[sku_id]['coupon']))
        max_width['name'] = max(max_width['name'], get_length(_sku_info[sku_id]['name']))
    max_width['price'] = max(max_width['price'], get_length('price'))
    max_width['stock'] = max(max_width['stock'], get_length('stock'))
    max_width['coupon'] = max(max_width['coupon'], get_length('coupon'))
    max_width['name'] = max(max_width['name'], get_length('name'))
    contents = [align_string('price', max_width['price'], 0) + ' | '
                + align_string('stock', max_width['stock'], 0) + ' | '
                + align_string('coupon', max_width['coupon'], 0) + ' | '
                + align_string('name', max_width['name'], 0),
                align_string('', max_width['price'], 0, '-') + '-+-'
                + align_string('', max_width['stock'], 0, '-') + '-+-'
                + align_string('', max_width['coupon'], 0, '-') + '-+-'
                + align_string('', max_width['name'], 0, '-')]
    for sku_id in _sku_info:
        contents.append(align_string(_sku_info[sku_id]['price'], max_width['price'], 1) + ' | '
                        + align_string(_sku_info[sku_id]['stock'], max_width['stock'], 0) + ' | '
                        + align_string(_sku_info[sku_id]['coupon'], max_width['coupon'], 0) + ' | '
                        + align_string(_sku_info[sku_id]['name'], max_width['name'], 0))
    global _out_path
    if _out_path is None:
        for line in contents:
            print(line)
    else:
        with codecs.open(_out_path, 'w', 'utf-8') as fp:
            for line in contents:
                fp.write(line + os.linesep)


if __name__ == '__main__':
    handle_argv()
    get_info_in_file()
    generate_sku_info()
    show_sku_info()
