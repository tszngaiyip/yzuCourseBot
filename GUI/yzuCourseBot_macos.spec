# -*- mode: python ; coding: utf-8 -*-
# macOS 專用 PyInstaller spec 檔案

from PyInstaller.utils.hooks import collect_data_files, collect_submodules, collect_dynamic_libs

block_cipher = None

a = Analysis(
    ['yzuCourseBot_GUI.py'],
    pathex=[],
    binaries=[],
    datas=[('../model.onnx', '.')],  # 包含 model.onnx
    hiddenimports=[
        # 核心套件
        'onnxruntime',
        'cv2',
        'numpy',
        'requests',
        'bs4',
        'lxml',
        'PIL',
        # Flet (相關 hook 會處理其他依賴)
        'flet',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # 排除開發工具
        'pytest',
        'IPython',
        'jupyter',
        'notebook',
        # 排除不需要的數據分析工具
        'matplotlib',
        'pandas',
        'scipy',
        # 排除 Tkinter (使用 Flet GUI)
        'tkinter',
        'Tkinter',
        '_tkinter',
        'tk',
        'tcl',
        # 排除 Flet Web/CLI 組件 (只需要 desktop)
        'flet.cli',
        'flet_cli',
        'flet_web',
        'uvicorn',
        'fastapi',
        'starlette',
        'cookiecutter',
        # 排除其他不需要的套件
        'pydoc',
        'doctest',
    ],
    cipher=block_cipher,
    noarchive=False,
)

# [FIX] 系統性解決 macOS codesign 失敗問題
# Flet 的 macOS 客戶端包含多個結構不標準的 framework (如 objective_c, rive_native)
# 導致 PyInstaller 的 codesign 程序崩潰。
# 解決方案：將這些元件從 a.binaries (二進位) 移至 a.datas (資料)，
# 這樣 PyInstaller 就只會進行複製，而不會嘗試對其重新簽章。
def reclassify_flet_binaries(analysis):
    flet_binaries = []
    remaining_binaries = []
    
    # 識別所有來自 Flet 的二進位檔
    for b in analysis.binaries:
        dest, src, type_ = b
        if 'flet_desktop' in dest or 'flet_cli' in dest:
            # 轉換為數據格式 (dest, src, 'DATA')
            flet_binaries.append((dest, src, 'DATA'))
        else:
            remaining_binaries.append(b)
            
    analysis.binaries = remaining_binaries
    analysis.datas.extend(flet_binaries)

reclassify_flet_binaries(a)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,  # onedir 模式：二進位檔與 exe 分開存放
    name='yzuCourseBot',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # 關閉 UPX 壓縮以兼容 TensorFlow dylib
    console=False,  # 不顯示終端機視窗，只顯示 GUI
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name='yzuCourseBot',
)

app = BUNDLE(
    coll,
    name='元智選課機器人.app',
    icon='../pic/icon.icns',  # 指定 macOS 使用的 .icns 圖示檔案
    bundle_identifier='com.yzucoursebot.app',
    info_plist={
        'CFBundleDisplayName': '元智選課機器人',
        'CFBundleShortVersionString': '2.0.3',
        'NSHighResolutionCapable': True,
        'LSMinimumSystemVersion': '12.0',
        'LSUIElement': True,
    },
)
