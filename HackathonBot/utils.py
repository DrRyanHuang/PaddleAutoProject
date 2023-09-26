import requests
import time
import json
import re

from config import config, logger

issue_token = config['issue_token']

comment_token = config['comment_token']

issue_headers = {'Authorization': f'token {issue_token}', 'Accept': 'application/vnd.github.raw+json', 'X-GitHub-Api-Version': '2022-11-28'}

comment_headers = {'Authorization': f'token {comment_token}', 'Accept': 'application/vnd.github.raw+json', 'X-GitHub-Api-Version': '2022-11-28'}

proxies = config['proxies']

issue_url = config['issue_url']

# 总的任务数量
task_num = config['task_num']

# 黑客松开始时间，只会统计黑客松开始时间之后的PR
start_time = config['start_time']

# 每列的名称
column_name = ['num', 'direction', 'state']

# 忽略不处理的题号，这部分留给人工处理
un_handle_tasks = config['un_handle_tasks']

# 已删除的赛题
removed_tasks = config['removed_tasks']

# 每个赛道所包含的赛题，每个赛道是一个数组
task_types = config['task_types']

type_names = config['type_names']

comment_to_user_list = []


def request_get_issue(url, params={}):
    """
    @desc: 返回单条issue
    """
    response = requests.get(url, headers=comment_headers, proxies=proxies, params=params)
    response = response.json()
    return response


def request_get_multi(url, params={}):
    """
    @desc: 根据url获取请求, 将回复转为json格式，注意会返回某个时间之前所有的回复
    """
    # 总的结果汇总
    result = []

    # 模糊查询title （TODO: Rest API 没有提供此功能，可能需要 GraphQL API）
    # params["head"] = "in:title+Hackathon"
    params["per_page"] = 100
    
    # 当前时间
    curTime = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.localtime())
    # 当前请求页
    page = 1

    while curTime > start_time:
        # 请求结果
        params['page'] = page
        response = requests.get(url, headers=comment_headers, proxies=proxies, params=params)
        response = response.json()

        # 如果已经没有PR了，直接返回已有的
        if len(response) == 0:
            return result
        
        # 合并结果
        result.extend(response)
        
        # 更新当前时间和请求页 
        curTime = response[-1]['created_at']
        page += 1
    
    return result


def comment_to_user(data):
    """
    desc: 在issue下回复（报名格式、编号错误， pr 编号错误）

    params:
        data: comment 内容
    """
    # 如果已经回复过了，不再回复
    if data['id'] in comment_to_user_list:
        return
    data = json.dumps(data)
    response = requests.post(issue_url + '/comments', data=data, headers=comment_headers, proxies=proxies)
    response = response.json()
    return response


def request_update_issue(url, data):
    """
    desc: 更新issue内容

    params:
        url: str 推送的url地址
        data: str 推送的issue内容
    """
    response = requests.patch(url, data=data, headers=issue_headers, proxies=proxies)
    response = response.json()
    return response


def process_issue(task_text):
    """
    desc: 从文本中提取题目列表，并封装为题目对象

    params:
        task_text: str 题目列表文本

    return:
        task_list: [] 对象格式的题目列表，每一列都是对象的一个属性，用字符串表示
    """
    task_list = []
    for i in range(task_num):
        start = task_text.find('| {} |'.format(i + 1))
        # 如果没有找到该编号的任务，直接返回
        if start < 0:
            logger.info('没有从issue内容中找到编号为【{}】的赛题'.format(str(i + 1)))
            task_list.append(None)
            continue
        end = start + 1
        column = 0
        task = {}
        while end < len(task_text) and task_text[end] != '\r' and task_text[end] != '\n':
            if (task_text[end] == '|'):
                item_content = task_text[start + 1: end]
                start = end            
                item_content = item_content.strip(' ')
                task[column_name[column]] = item_content
                column += 1
            end += 1
        task_list.append(task)
    
    return task_list


def update_status_by_comment(tasks, comment):
    """
    desc: 根据评论更新表格内容

    params:
        tasks: 处理后的task对象数组
        comment: 处理后的comment对象

    """

    # 提取评论信息，将字符串格式化为对象
    comment = process_comment(comment)

    if comment == None:
        return
    
    # 依次更新评论中提到的每个题目
    if 'num' in comment:
        for i in range(0, len(comment['num'])):

            num = comment['num'][i]

            # 如果报名的赛题编号错误
            if num > len(tasks) or num <= 0:
                comment_to_user({"body": "@{} 赛题编号【{}】不存在".format(comment['username'], num), "id": "comment-" + str(comment["id"])})
                comment_to_user_list.append('comment-' + str(comment["id"]))
                logger.error('@{} 赛题编号【{}】不存在：'.format(comment['username'], str(num)))
                return
                
            # 对于手工修改的task，无需进行处理
            if num in un_handle_tasks:
                return
            
            # 对于删除的赛题，需要进行提醒赛题已删除
            if num in removed_tasks:
                logger.error('@{} 赛题【{}】已被删除'.format(comment['username'], str(num)))
                comment_to_user({"body": "@{} 抱歉，赛题【{}】已删除".format(comment['username'], num), "id": 'comment-' + str(comment["id"])})
                comment_to_user_list.append('comment-' + str(comment["id"]))
                return

            task = tasks[num - 1]

            if task == None:
                logger.error('赛题【{}】没有出现在任务列表中'.format(num))
                return

            update_status = {
                'username': comment['username'],
                'status': '报名' if comment["type"] == "apply" else "提交作品",
                'pr': [] if comment["type"] == "apply" else comment["pr"]
            }
            task['state'] = get_updated_status(task['state'], update_status)
            

def process_comment(comment):
    """
    @desc: 提取评论信息，将字符串化的status转化为对象信息
    """
    if comment['user']['login'] == 'HackathonBot':
        return None
        
    comment_obj = {}
    # 获取评论者的用户名和评论内容
    comment_obj['username'] = comment['user']['login']
    content = comment['body']
    comment_obj['created_at'] = comment['created_at']
    comment_obj['id'] = comment['id']

    content = content.replace('：',':').replace('，', ',').replace(',', '、')

    # 只更新报名信息
    if '报名:' in content and '【报名】:' not in content:
        logger.error('@{} 报名的格式不正确'.format(comment_obj['username']))
        comment_to_user({"body": "@{} 请检查报名格式，正确的格式为【报名】: 题目编号".format(comment_obj['username']), "id": 'comment-' + str(comment["id"])})
        comment_to_user_list.append('comment-' + str(comment["id"]))
        return None

    if content.find("【报名】") != -1:
        comment_obj["type"] = "apply"
        
        # 获取题号
        start = content.find("【报名】")

        while content[start] < '0' or content[start] > '9':
            start += 1
        end = start + 1
        while end < len(content) and content[end] != '\r' and content[end] != '\n':
            end += 1
        
        # 题号用顿号隔开或-隔开
        sequence = content[start: end].strip(' ')
        if '-' in sequence:
            nums = sequence.split('-')
            nums = [int(num) for num in nums]
            nums = [i for i in range(nums[0], nums[1] + 1)]
        else:
            nums = sequence.split('、')
            nums = [int(num) for num in nums]
        comment_obj['num'] = nums

        logger.info('{} 报名赛题 {}'.format(comment_obj['username'], str(nums)))

        return comment_obj
    
    elif content.find("【提交】") != -1:
        comment_obj["type"] = "commit"

        # 获取题号
        start = content.find("【提交】")

        while content[start] < '0' or content[start] > '9':
            start += 1
        end = start + 1
        while end < len(content) and content[end] != '\r' and content[end] != '\n':
            end += 1
        
        # 题号用顿号隔开或-隔开
        sequence = content[start: end].strip(' ')
        if '-' in sequence:
            nums = sequence.split('-')
            nums = [int(num) for num in nums]
            nums = [i for i in range(nums[0], nums[1] + 1)]
        else:
            nums = sequence.split('、')
            nums = [int(num) for num in nums]
        comment_obj['num'] = nums
        
        start = content.find("作品链接】")
        start = content.find("http", start)
        issues = content[start: ]
        issues = issues.replace("\n", "、")
        issues = issues.split("、")
        issues = [issue.strip(" ") for issue in issues]
        issues = ['[{}]({})'.format(issue[issue.rfind('/')+ 1:], issue) for issue in issues]
        comment_obj["pr"] = issues

        return comment_obj

    return None


def get_updated_status(ori_status, update_status):
    """
    @desc: 根据表格原先的状态信息更新状态，姓名，状态（报名状态、提交RFC、完成设计文档、提交PR、锁定任务、完成任务），PR
        * 注意：不同用户的状态通过<br>分隔
    
    params:
        ori_status: str 原先状态栏的字符串表示
        update_status: dict 更新状态的对象表示，该对象包含 username:str 用户名; status:str 变更后状态；pr:dict pr列表
    """
    # 寻找之前的PR
    prs = ''
    user_status = None

    # 如果用户出现在状态列表中，则需要保留之前的PR
    if update_status['username'] in ori_status:
        start = ori_status.find(update_status['username'])
        end = ori_status.find('<br>', start)
        user_status = ori_status[start: end].strip(' ')
        start = user_status.find('[')
        if start != -1:
            prs = user_status[start:]
    
    # 新加入PR
    for pr in update_status['pr']:
        if pr not in prs:
            prs = prs + ' ' + pr
    
    # 更新状态前需要判断是否可以更新，状态级别只能增大，不能减小
    ori_status_level = get_status_level(user_status)
    update_status_level = get_status_level(update_status["status"])

    if ori_status_level < update_status_level:
        if update_status['status'] == '报名':
            badge = '<img src="https://img.shields.io/badge/状态-报名-2ECC71" />'
        elif update_status['status'] == '提交作品':
            badge = '<img src="https://img.shields.io/badge/状态-提交作品-F39C12" />'
    else:
        # 如果不需要变更用户状态，则沿用之前的状态
        start = user_status.find("<img")
        end = user_status.find("/>")
        if start != -1 and end != -1:
            badge = user_status[start: end + 2]

    
    # 格式化当前用户的状态
    status = '@{} {} {}'.format(update_status['username'], badge, prs)
    
    # 如果该用户存在则替换
    if '@' + update_status['username'] in ori_status:
        start = ori_status.find('@' + update_status['username'])
        end = ori_status.find('<br>', start)
        ori_status = f'{ori_status[ :start]}{status}{ori_status[end: ]}'
    # 否则追加
    else:
        ori_status += '{}<br> '.format(status)

    return ori_status


def get_status_level(status):

    """
    desc: 根据字符串形式的状态获取数字形式的状态编号
    
    params:
        status: str 文本形式的状态

    return:
        status_level: int 数字形式的状态
    """

    if status == None:
        return 0
    
    status_level = 0

    if "报名" in status:
        status_level = 1
    elif "提交作品" in status:
        status_level = 2

    return status_level


def update_board(tasks):
    """
    desc: 根据任务对象列表获取看板信息

    params:
        tasks: 任务列表对象
    """

    board_head = "| 任务方向 | 任务数量 | 提交作品 / 任务认领 | 提交率 | 完成 | 完成率 |\n| :----: | :----: | :----:  | :----: | :----: | :----: |\n"

    for i in range(len(task_types)):
        type_name = type_names[i]
        task_num, claimed, submitted, completed = len(task_types[i]), 0, 0, 0
        
        for task_id in task_types[i]:
            if task_id > len(tasks):
                continue
            task = tasks[task_id - 1]
            if task == None:
                continue
            status = task["status"]
            if "完成任务" in status:
                completed += 1
                submitted += 1
                claimed += 1
            elif "提交PR" in status:
                submitted += 1
                claimed += 1
            elif "提交RFC" in status or "完成设计文档" in status or "报名" in status:
                claimed += 1
        
        row = '| {} | {} | {} / {} | {}% | {} | {}% |\n'.format(type_name, task_num, submitted, claimed, round(submitted / task_num * 100, 2), completed, round(completed / task_num * 100, 2), round(completed / task_num * 100, 2))

        board_head += row

    return board_head
