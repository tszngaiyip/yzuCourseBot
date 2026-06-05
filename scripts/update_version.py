import re
import sys
import os

def update_file(filepath, pattern, replacement):
    if not os.path.exists(filepath):
        print(f"找不到檔案: {filepath}")
        return False
        
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
        
    new_content, count = re.subn(pattern, replacement, content)
    
    if count > 0:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"已更新: {filepath} ({count} 處)")
        return True
    else:
        print(f"未找到需更新的內容或版本號已是最新: {filepath}")
        return False

def main():
    if len(sys.argv) < 2:
        print("用法: python update_version.py <新版本號>")
        print("範例: python update_version.py 2.0.4")
        sys.exit(1)
        
    # 如果傳入的標籤帶有 'v'，自動剝除 (例如 v2.0.4 -> 2.0.4)
    new_version = sys.argv[1]
    if new_version.startswith('v'):
        new_version = new_version[1:]
        
    print(f"準備將版本號更新為: {new_version}\n")
    
    # 專案根目錄 (腳本在 scripts/ 下，所以往上一層)
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # 檔案路徑與正則替換規則
    files_to_update = [
        {
            'path': os.path.join(root_dir, 'GUI', 'yzuCourseBot_GUI.py'),
            'pattern': r'ft\.Text\("版本: [0-9\.]+",',
            'replacement': f'ft.Text("版本: {new_version}",'
        },
        {
            'path': os.path.join(root_dir, 'mobile_app', 'main.py'),
            'pattern': r'text: "版本: [0-9\.]+"',
            'replacement': f'text: "版本: {new_version}"'
        },
        {
            'path': os.path.join(root_dir, 'mobile_app', 'buildozer.spec'),
            'pattern': r'^version = [0-9\.]+',
            'replacement': f'version = {new_version}'
        },
        {
            'path': os.path.join(root_dir, 'GUI', 'yzuCourseBot_macos.spec'),
            'pattern': r"'CFBundleShortVersionString': '[0-9\.]+'",
            'replacement': f"'CFBundleShortVersionString': '{new_version}'"
        }
    ]
    
    for item in files_to_update:
        # buildozer.spec 中正則需要用到 ^，所以替換時開啟 re.MULTILINE
        if 'buildozer.spec' in item['path']:
            with open(item['path'], 'r', encoding='utf-8') as f:
                content = f.read()
            new_content, count = re.subn(item['pattern'], item['replacement'], content, flags=re.MULTILINE)
            if count > 0:
                with open(item['path'], 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print(f"已更新: {item['path']} ({count} 處)")
            else:
                print(f"未找到需更新的內容或版本號已是最新: {item['path']}")
        else:
            update_file(item['path'], item['pattern'], item['replacement'])
            
    print("\n版本號同步完成！")

if __name__ == '__main__':
    main()
