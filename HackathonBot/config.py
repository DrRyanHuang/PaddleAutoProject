import logging
import os

# 监控的仓库列表
repo_urls = ['https://api.github.com/repos/PaddlePaddle/Paddle/pulls',
             'https://api.github.com/repos/PaddlePaddle/community/pulls',
             'https://api.github.com/repos/PaddlePaddle/PaddleScience/pulls',
             'https://api.github.com/repos/PaddlePaddle/PaddleOCR/pulls',
             'https://api.github.com/repos/PaddlePaddle/PaddleClas/pulls',
             'https://api.github.com/repos/PaddlePaddle/PaddleSeg/pulls',
             'https://api.github.com/repos/PaddlePaddle/PaddleDetection/pulls',
             'https://api.github.com/repos/PaddlePaddle/PaddleNLP/pulls',
             'https://api.github.com/repos/PaddlePaddle/Paddle3D/pulls',
             'https://api.github.com/repos/PaddlePaddle/PaddleMIX/pulls',
             'https://api.github.com/repos/PaddlePaddle/Paddle2ONNX/pulls',
             'https://api.github.com/repos/ArmDeveloperEcosystem/Paddle-examples-for-AVH/pulls',
             'https://api.github.com/repos/openvinotoolkit/openvino/pulls',
             'https://api.github.com/repos/PaddlePaddle/PaddleCustomDevice/pulls'
            ]

config = {
    # 更新issue的token
    'issue_token': os.environ.get('ISSUE_TOKEN'),

    # 更新评论的token
    'comment_token': os.environ.get('COMMENT_TOKEN'),

    # 代理地址
    'proxies': {
        'http': os.environ.get('HTTP_PROXY'),
        'https': os.environ.get('HTTPS_PROXY')
    },

    # 黑客松开始时间，只会统计黑客松开始时间之后的PR(注意时间中的字母T和Z不能缺少)
    'start_time' : '2023-09-23T00:28:48Z',

    # 黑客松 issue页面 url 地址, 注意结尾不要有斜杠
    'issue_url': 'https://api.github.com/repos/PaddlePaddle/Paddle/issues/57585',

    # 监控的仓库列表
    'repo_urls': [],

    # 总的任务数量
    'task_num' : 2,

    # 忽略不处理的题号，这部分留给人工处理
    'un_handle_tasks' : [],

    # 已删除的赛题
    'removed_tasks' : [],

    # 赛道名
    'type_names' : ["热身赛", "框架 API 开发任务", "框架其他开发任务", "科学计算模型复现", "套件开发任务"], 

    # 每个赛题所属的赛道，每个赛道是一个数组
    'task_types' : [[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11],
                    [12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41],
                    [42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52],
                    [53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63],
                    [64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82]],

}

def get_logger():
    logger = logging.getLogger('logger')
    logger.setLevel(level=logging.DEBUG)

    formatter = logging.Formatter('%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s')

    file_handler = logging.FileHandler('./logs/output.txt', encoding='utf-8')
    file_handler.setLevel(level=logging.INFO)
    file_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

    return logger

logger = get_logger()
