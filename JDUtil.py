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
_area_code = '16_1315_1316_53522'
_in_path = './in.txt'
_sku_info = {}
_sku_ids = {}

double_byte_rule = re.compile('<strong>([\u4e00-\u9fa5]+)</strong>|(\d+)')
product_rule = re.compile('<div class=\"p-name\">([^<]*)</div>')
sku_ids_rule = re.compile('https://item.jd.com/(\d+)')
url_rule = re.compile('[a-zA-z]+://[^\s]*')
get_value_behind_equality_sign_rule = re.compile('=(.*)')


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
    return regex_result(sku_ids_rule, url)


def get_value_behind_equality_sign(string):
    return regex_result(get_value_behind_equality_sign_rule, string)


def get_product_name(sku_id):
    url = 'https://item.jd.com/' + sku_id + '.html'
    contents = get_html_content(url)
    return regex_result(product_rule, contents)


def get_param_value_in_url(url, param):
    rule = re.compile('(?<=' + param + '=)(\d+)')
    return regex_result(rule, url)


def get_product_price(sku_id):
    url = 'http://p.3.cn/prices/mgets?skuIds=' + sku_id
    json_resp = get_html_content(url)
    json_obj = simplejson.loads(json_resp)
    return json_obj[0]['p']


def get_product_stock(sku_id, area_code):
    url = 'https://c0.3.cn/stock?skuId=' + sku_id + '&area=' + area_code + '&cat=1,2,3&extraParam={"originid":"1"}'
    json_resp = get_html_content(url)
    json_obj = simplejson.loads(json_resp)['stock']
    # result = double_byte_rule.sub('', json_obj['stockDesc'])
    return regex_result(double_byte_rule, json_obj['stockDesc'], True, ':')


def get_product_coupon(sku_id, area_code):
    url = 'https://cd.jd.com/promotion/v2?skuId=' + sku_id + '&area=' + area_code + '&cat=1,2,3'
    json_resp = get_html_content(url)
    json_obj = simplejson.loads(json_resp)
    coupon_list = json_obj['skuCoupon']
    if len(coupon_list) == 0:
        return ''
    result = ''
    for info in coupon_list:
        result += str(info['quota']) + '-' + str(info['discount']) + ', '
    result = result[:-2]
    return result


def get_length(string):
    length = len(string)
    utf8_length = len(string.encode('utf-8'))
    return ((utf8_length - length) >> 1) + length


def align_string(string, width, align_type=1, fill_char=' '):
    length = get_length(string)
    if width <= length:
        return string
    # -1: left, 0: center, 1: right
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


def check_area_code(area_code):
    area_ids = area_code.split('_')
    length = len(area_ids)
    if length < 2:
        return False
    for idx in range(0, length - 1):
        json_obj = get_area_code_info(area_ids[idx])
        if json_obj is None:
            return False
        int_area_id = int(area_ids[idx + 1])
        has_next_area_id = False
        for obj in json_obj:
            if int_area_id == obj['id']:
                has_next_area_id = True
                break
        if not has_next_area_id:
            return False
    return True


def generate_area_code():
    global _area_code
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

        for obj in json_obj:
            print('name: ' + obj['name'] + ', id: ' + str(obj['id']))
        area_id = input('请选择所在区域: ')
        int_area_id = int(area_id)
        for obj in json_obj:
            if int_area_id == obj['id']:
                gen_area_code += area_id + '_'
                area_name += obj['name'] + '-'
                cur_area_id = area_id
                break


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


def store_sku_id(new_sku_id):
    global _in_path, _sku_ids
    # 避免重复读取
    if not _sku_ids:
        contents = read_file(_in_path, 'utf-8', True, True)
        if contents is None:
            return False
        for line in contents:
            sku_id = get_sku_id(line)
            _sku_ids[sku_id] = True
    if new_sku_id in _sku_ids:
        return True
    with codecs.open(_in_path, 'w+', 'utf-8') as fp:
        fp.write(os.linesep + 'https://item.jd.com/' + new_sku_id + '.html' + os.linesep)
    return True


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


def get_sku_id_and_area_code():
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


def handle_argv():
    option_result = False

    # 在参数前面根据优先级加字符，然后排序
    # argv = sys.argv[1:]
    # for idx in range(0, len(argv)):
    #     if -1 != sys.argv[idx].find('-gen_area_code'):
    #         argv[idx] = '9' + argv[idx]
    #     elif -1 !=

    # for idx in range(1, len(sys.argv)):
    #     if -1 != sys.argv[idx].find('-gen_area_code'):
    #         generate_area_code()
    #         flag = store_area_code()
    #     elif sys.argv[idx].find('-add='):
    #         sku_id = get_value(sys.argv[idx])
    #         flag = store_sku_id(sku_id)
    #     elif sys.argv[idx].find('-area_code='):
    #         area_code_tmp = get_value(sys.argv[idx])
    #         flag = check_area_code(area_code_tmp)
    #     elif sys.argv[idx].find('-in_path='):
    #         if path.exists()


def gen_sku_info():
    global _sku_info
    for sku_id in _sku_ids:
        _sku_info[sku_id] = {}
        _sku_info[sku_id]['price'] = get_product_price(sku_id)
        _sku_info[sku_id]['stock'] = get_product_stock(sku_id, _area_code)
        _sku_info[sku_id]['coupon'] = get_product_coupon(sku_id, _area_code)
        _sku_info[sku_id]['name'] = get_product_name(sku_id)


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
    print(align_string('price', max_width['price'], 0) + ' | '
          + align_string('stock', max_width['stock'], 0) + ' | '
          + align_string('coupon', max_width['coupon'], 0) + ' | '
          + align_string('name', max_width['name'], 0))
    print(align_string('', max_width['price'], 0, '-') + '-+-'
          + align_string('', max_width['stock'], 0, '-') + '-+-'
          + align_string('', max_width['coupon'], 0, '-') + '-+-'
          + align_string('', max_width['name'], 0, '-'))
    for sku_id in _sku_info:
        print(align_string(_sku_info[sku_id]['price'], max_width['price'], 1) + ' | '
              + align_string(_sku_info[sku_id]['stock'], max_width['stock'], 0) + ' | '
              + align_string(_sku_info[sku_id]['coupon'], max_width['coupon'], 0) + ' | '
              + align_string(_sku_info[sku_id]['name'], max_width['name'], 0))


if __name__ == '__main__':
    handle_argv()
    get_sku_id_and_area_code()
    gen_sku_info()
    show_sku_info()
