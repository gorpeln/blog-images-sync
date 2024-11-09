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

# 收集需要上传的文件
def collect_files_to_upload(base_path='/'):
    files_to_upload = []
    try:
        # 列出又拍云上的所有文件和文件夹
        files = up.getlist(base_path)
        for file in files:
            full_path = os.path.join(base_path, file['name']).lstrip('/')
            print(f"Processing: {full_path}")
            
            if file['type'] == 'F':  # 文件夹
                # 递归处理文件夹
                files_to_upload.extend(collect_files_to_upload(full_path))
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
                        repo.get_contents(filename)
                        print(f"File {filename} already exists in GitHub.")
                    except GithubException as e:
                        if e.status == 404:
                            print(f"File {filename} does not exist in GitHub, adding to upload list...")
                            files_to_upload.append((filename, content))
                        else:
                            print(f"Error: {e}")
                except GithubException as e:
                    print(f"Error accessing repository: {e}")
    except upyun.UpYunServiceException as e:
        print(f"UpYun Service Exception: {e}")
    except Exception as e:
        print(f"General Exception: {e}")
    
    return files_to_upload

# 批量上传文件
def batch_upload_files(files_to_upload):
    try:
        repo = gh.get_user(REPO_OWNER).get_repo(REPO_NAME)
        commit_message = "Batch upload images"
        tree_elements = []

        for filename, content in files_to_upload:
            # 将内容写入临时文件
            local_filename = os.path.basename(filename)
            local_path = os.path.join('/tmp', local_filename)
            with open(local_path, 'wb') as f:
                f.write(content)
            
            with open(local_path, 'rb') as f:
                # 创建树元素
                blob = repo.create_git_blob(f.read(), "base64")
                tree_elements.append({
                    "path": filename,
                    "mode": "100644",
                    "type": "blob",
                    "sha": blob.sha
                })
            
            if os.path.exists(local_path):
                os.remove(local_path)  # 清理临时文件
        
        # 创建树
        tree = repo.create_git_tree(tree_elements, repo.get_git_tree(BRANCH_NAME))
        
        # 获取最新提交
        latest_commit = repo.get_branch(BRANCH_NAME).commit
        
        # 创建新提交
        new_commit = repo.create_git_commit(commit_message, tree, [latest_commit])
        
        # 更新分支
        ref = repo.get_git_ref(f"heads/{BRANCH_NAME}")
        ref.edit(new_commit.sha)
        
        print("All files have been uploaded to GitHub.")
    except GithubException as e:
        print(f"Error during batch upload: {e}")

if __name__ == '__main__':
    files_to_upload = collect_files_to_upload()
    if files_to_upload:
        batch_upload_files(files_to_upload)
    else:
        print("No new files to upload.")