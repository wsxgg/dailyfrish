from django.core.files.storage import Storage
from django.conf import settings
from fdfs_client.client import Fdfs_client, get_tracker_conf

class FDFSStorage(Storage):
    # 自定义文件存储类

    def __init__(self, client_conf=None, base_url=None):
        if client_conf is None:
            client_conf = settings.FDFS_CLIENT_CONF
        self.client_conf = client_conf
        if base_url is None:
            base_url = settings.FDFS_URL
        self.base_url = base_url

    def open(self, name, mode='rb'):
        # 打开文件的方法
        pass

    def save(self, name, content, max_length=None):
        # 保存文件使用的方法。 name为文件名， content为上传文件内容的File对象。
        # 1. 创建一个Fdfs_client对象，连接fastdfs数据库
        tracker_path = get_tracker_conf(self.client_conf)
        client = Fdfs_client(tracker_path)
        # 2. 根据内容上传文件
        res = client.upload_by_buffer(content.read())
        # res格式：
        # dict {
        #     'Group name': group_name,
        #     'Remote file_id': remote_file_id,
        #     'Status': 'Upload successed.',        上传成功时的状态码
        #     'Local file name': '',
        #     'Uploaded size': upload_size,
        #     'Stroage IP': stroage_ip
        # }
        if res.get('Status') != 'Upload successed.':
            # 上传失败
            raise Exception('上传文件到fast dfs 失败')
        # 获取返回文件id
        filename = res.get('Remote file_id')
        return filename.decode()

    def exists(self, name):
        # 判断文件名name是否存在，存在返回True，不存在返回False
        # 因为我们使用文件内容存放在fastdfs的，直接返回False即可
        return False

    def url(self, name):
        # 返回访问文件的url
        return self.base_url+name

