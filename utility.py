from zipfile import ZipFile



def unzip():
    zip_file = 'content.zip'
    password = 'h;DFaR%EQ&2~u*<'
    with ZipFile(zip_file) as zf:
        zf.extractall(pwd=bytes(password,'utf-8'))