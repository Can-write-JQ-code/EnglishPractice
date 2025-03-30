import os
import pymysql
from dotenv import load_dotenv
import glob
import re

# 加载环境变量
load_dotenv()

# 获取MySQL连接信息
host = os.getenv("MYSQL_HOST", "localhost")
port = int(os.getenv("MYSQL_PORT", "3306"))
user = os.getenv("MYSQL_USER", "root")
password = os.getenv("MYSQL_PASSWORD", "")
db = os.getenv("MYSQL_DB", "english_practice")

def create_database():
    """创建数据库（如果不存在）"""
    try:
        # 连接MySQL服务器（不指定数据库）
        conn = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password
        )
        cursor = conn.cursor()
        
        # 创建数据库
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db} DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        print(f"数据库 {db} 已创建或已存在")
        
        conn.close()
    except Exception as e:
        print(f"创建数据库时出错: {e}")
        return False
    return True

def clean_sql_statement(statement):
    """清理SQL语句，处理常见的语法问题"""
    # 移除注释
    statement = re.sub(r'--.*?$', '', statement, flags=re.MULTILINE)
    
    # 如果是空语句，返回空字符串
    if not statement.strip():
        return ""
    
    # 处理引号问题
    statement = statement.replace("'", "'").replace("'", "'")
    
    # 处理中文引号
    statement = statement.replace(""", '"').replace(""", '"')
    
    return statement.strip()

def import_sql_file(file_path):
    """导入SQL文件到数据库"""
    try:
        # 连接到数据库
        conn = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=db,
            charset='utf8mb4'
        )
        cursor = conn.cursor()
        
        # 读取SQL文件
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                sql_content = f.read()
        except UnicodeDecodeError:
            # 如果UTF-8解码失败，尝试GBK编码
            with open(file_path, 'r', encoding='gbk') as f:
                sql_content = f.read()
        
        # 处理CREATE TABLE语句
        if "CREATE TABLE" in sql_content.upper():
            # 提取表名
            table_name_match = re.search(r'CREATE\s+TABLE\s+[`"]?(\w+)[`"]?', sql_content, re.IGNORECASE)
            if table_name_match:
                table_name = table_name_match.group(1)
                
                # 先删除表（如果存在）
                cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
                
                # 修改CREATE TABLE语句，确保使用正确的字符集
                sql_content = re.sub(
                    r'ENGINE\s*=\s*\w+(\s+.*?)?;',
                    r'ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;',
                    sql_content,
                    flags=re.IGNORECASE
                )
        
        # 分割SQL语句并执行
        statements = sql_content.split(';')
        for statement in statements:
            clean_stmt = clean_sql_statement(statement)
            if clean_stmt:
                try:
                    cursor.execute(clean_stmt)
                except Exception as e:
                    print(f"执行语句时出错: {e}")
                    print(f"问题语句: {clean_stmt[:100]}...")
        
        conn.commit()
        print(f"成功导入SQL文件: {os.path.basename(file_path)}")
        conn.close()
        return True
    except Exception as e:
        print(f"导入SQL文件 {file_path} 时出错: {e}")
        return False

def main():
    """主函数"""
    # 创建数据库
    if not create_database():
        print("无法创建数据库，程序退出")
        return
    
    # 获取所有SQL文件
    sql_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                          "english-vocabulary-master", "乱序sql")
    sql_files = glob.glob(os.path.join(sql_dir, "*.sql"))
    
    if not sql_files:
        print(f"在 {sql_dir} 中未找到SQL文件")
        return
    
    # 导入所有SQL文件
    for sql_file in sql_files:
        import_sql_file(sql_file)
    
    print("所有SQL文件导入完成")

if __name__ == "__main__":
    main()
