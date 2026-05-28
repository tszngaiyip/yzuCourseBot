# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_data_files, collect_submodules, collect_dynamic_libs

block_cipher = None

a = Analysis(
    ['yzuCourseBot_GUI.py'],
    pathex=[],
    binaries=[],
    datas=[('model.onnx', '.')],  # 包含 model.onnx，Flet 相關由 hook 自動處理
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
        'flet_core',
        'flet_runtime',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],  # 移除自定義 hook，使用 Flet 內建 hook
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
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='元智選課機器人',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # 關閉 UPX 壓縮以兼容 Flet/TensorFlow DLL
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # 不顯示終端機視窗，只顯示 GUI
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # 可以在這裡指定 .ico 圖示檔案
)

