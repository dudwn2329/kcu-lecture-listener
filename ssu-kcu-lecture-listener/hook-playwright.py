from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

datas = collect_data_files('playwright', subdir='driver')
binaries = collect_dynamic_libs('playwright', subdir='driver')
