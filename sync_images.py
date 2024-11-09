import os
import upyun
from github import Github, GithubException

# 从环境变量中读取配置
UPYUN_BUCKET = os.getenv('UPYUN_BUCKET')
UPYUN_USERNAME = os.getenv('UPYUN_USERNAME')
UPYUN_PASSWORD = os.getenv('UPYUN_PASSWORD')

GH_TOKEN = os.getenv('GH_TOKEN')
REPO_NAME = os.getenv('REPO_NAME')
REPO_OWNER = os.getenv('REPO_OWNER')
BRANCH_NAME = 'master'  # 设置分支名称为 master

# 初始化又拍云和GitHub客户端
up = upyun.UpYun(UPYUN_BUCKET, UPYUN_USERNAME, UPYUN_PASSWORD)
gh = Github(GH_TOKEN)

# 同步函数
def sync_images(base_path='/'):
    try:
        # 列出又拍云上的所有文件和文件夹
        files = up.getlist(base_path)
        for file in files:
            full_path = os.path.join(base_path, file['name']).lstrip('/')
            print(f"Processing: {full_path}")
            
            if file['type'] == 'F':  # 文件夹
                # 递归处理文件夹
                sync_images(full_path)
            else:  # 文件
                filename = full_path
                content = up.get(full_path)
                
                # 确保 content 是字节对象
                if isinstance(content, str):
                    content = content.encode('utf-8')
                
                # 检查文件是否已存在于GitHub仓库
                try:
                    repo = gh.get_user(REPO_OWNER).get_repo(REPO_NAME)
                    try:
                        existing_file = repo.get_contents(filename)
                        print(f"File {filename} already exists in GitHub.")
                    except GithubException as e:
                        if e.status == 404:
                            print(f"File {filename} does not exist in GitHub, uploading...")
                            # 如果文件不存在，则上传
                            local_filename = os.path.basename(filename)
                            local_path = os.path.join('/tmp', local_filename)
                            with open(local_path, 'wb') as f:
                                f.write(content)  # 确保 content 是字节对象
                            with open(local_path, 'rb') as f:
                                repo.create_file(filename, "Add new image", f.read(), branch=BRANCH_NAME)
                            print(f"File {filename} has been uploaded to GitHub.")
                        else:
                            print(f"Error: {e}")
                except GithubException as e:
                    print(f"Error accessing repository: {e}")
                finally:
                    if os.path.exists(local_path):
                        os.remove(local_path)  # 清理临时文件
    except upyun.UpYunServiceException as e:
        print(f"UpYun Service Exception: {e}")
    except Exception as e:
        print(f"General Exception: {e}")

if __name__ == '__main__':
    sync_images()