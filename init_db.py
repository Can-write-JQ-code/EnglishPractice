import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String, Text, text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime

# 加载环境变量
load_dotenv()

# 内存中的单词数据，用于在MySQL不可用时使用
in_memory_words = [
    {"word": "apple", "meaning": "苹果", "level": "初级"},
    {"word": "banana", "meaning": "香蕉", "level": "初级"},
    {"word": "computer", "meaning": "电脑", "level": "初级"},
    {"word": "dictionary", "meaning": "字典", "level": "初级"},
    {"word": "education", "meaning": "教育", "level": "中级"},
    {"word": "friendship", "meaning": "友谊", "level": "中级"},
    {"word": "government", "meaning": "政府", "level": "中级"},
    {"word": "happiness", "meaning": "幸福", "level": "中级"},
    {"word": "information", "meaning": "信息", "level": "中级"},
    {"word": "journey", "meaning": "旅行", "level": "中级"},
    {"word": "knowledge", "meaning": "知识", "level": "中级"},
    {"word": "language", "meaning": "语言", "level": "中级"},
    {"word": "mountain", "meaning": "山脉", "level": "中级"},
    {"word": "notebook", "meaning": "笔记本", "level": "中级"},
    {"word": "opportunity", "meaning": "机会", "level": "高级"},
    {"word": "professor", "meaning": "教授", "level": "高级"},
    {"word": "question", "meaning": "问题", "level": "高级"},
    {"word": "restaurant", "meaning": "餐厅", "level": "高级"},
    {"word": "student", "meaning": "学生", "level": "初级"},
    {"word": "technology", "meaning": "技术", "level": "高级"},
    {"word": "university", "meaning": "大学", "level": "高级"},
    {"word": "vacation", "meaning": "假期", "level": "高级"},
    {"word": "weather", "meaning": "天气", "level": "初级"},
    {"word": "xylophone", "meaning": "木琴", "level": "高级"},
    {"word": "yesterday", "meaning": "昨天", "level": "初级"},
    {"word": "zoology", "meaning": "动物学", "level": "高级"}
]

# 定义SQLAlchemy基类
Base = declarative_base()

# 定义词汇表映射
class Word(Base):
    __tablename__ = 'words'
    
    id = Column(Integer, primary_key=True)
    word = Column(String(255), nullable=False)
    translate = Column(Text, nullable=False)
    level = Column(String(50), nullable=True)
    
    def __repr__(self):
        return f"<Word(word='{self.word}', translate='{self.translate}')>"

# 定义学习记录表
class LearnedWord(Base):
    __tablename__ = 'learned_words'
    
    id = Column(Integer, primary_key=True)
    word = Column(String(255), nullable=False)
    translate = Column(Text, nullable=False)
    level = Column(String(50), nullable=True)
    source_table = Column(String(50), nullable=True)  # 来源表
    learn_time = Column(DateTime, default=datetime.datetime.now)  # 学习时间
    review_count = Column(Integer, default=0)  # 复习次数
    last_review_time = Column(DateTime, nullable=True)  # 最后复习时间
    learn_stage = Column(Integer, default=1)  # 学习阶段：1=认识，2=填空，3=盲打，4=复习完成
    
    def __repr__(self):
        return f"<LearnedWord(word='{self.word}', translate='{self.translate}', review_count={self.review_count})>"

# 词汇表映射，键是表名，值是中文级别名称
VOCABULARY_TABLES = {
    'junior': '初中',
    'senior': '高中',
    'cet4': '四级',
    'cet6': '六级',
    'graduate': '考研',
    'toefl': '托福',
    'sat': 'SAT'
}

# 内存模式下的级别
MEMORY_LEVELS = ['初级', '中级', '高级']

# 全局变量，用于标记是否使用内存模式
use_in_memory = False
session = None
engine = None

def init_database():
    """初始化数据库连接和表结构"""
    global use_in_memory, session, engine
    
    # 获取数据库连接参数
    mysql_host = os.getenv('MYSQL_HOST', 'localhost')
    mysql_port = os.getenv('MYSQL_PORT', '3306')
    mysql_user = os.getenv('MYSQL_USER', 'root')
    mysql_password = os.getenv('MYSQL_PASSWORD', '')
    mysql_db = os.getenv('MYSQL_DB', 'english_practice')
    
    # 构建数据库连接URL
    db_url = f"mysql+pymysql://{mysql_user}:{mysql_password}@{mysql_host}:{mysql_port}/{mysql_db}"
    
    try:
        # 创建数据库引擎
        engine = create_engine(db_url, echo=False)
        
        # 创建会话
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # 测试连接
        session.execute(text("SELECT 1"))
        
        # 检查词汇表是否存在
        for table_name in VOCABULARY_TABLES.keys():
            try:
                count_query = text(f"SELECT COUNT(*) FROM {table_name}")
                result = session.execute(count_query).scalar()
                print(f"找到词汇表: {table_name}，包含 {result} 个单词")
            except Exception as e:
                print(f"词汇表 {table_name} 不存在或无法访问: {e}")
                print(f"请确保已导入SQL文件并创建了表 {table_name}")
        
        # 检查学习记录表是否存在
        try:
            count_query = text("SELECT COUNT(*) FROM learned_words")
            result = session.execute(count_query).scalar()
            print(f"找到学习记录表: learned_words，包含 {result} 条记录")
            
            # 检查learn_stage字段是否存在
            try:
                session.execute(text("SELECT learn_stage FROM learned_words LIMIT 1"))
                print("学习记录表已包含learn_stage字段")
            except Exception as e:
                print("学习记录表缺少learn_stage字段，正在添加...")
                session.execute(text("""
                    ALTER TABLE learned_words 
                    ADD COLUMN learn_stage INT DEFAULT 1 
                    COMMENT '学习阶段：1=认识，2=填空，3=盲打，4=复习完成'
                """))
                session.commit()
                print("已添加learn_stage字段到学习记录表")
                
        except Exception as e:
            print("学习记录表不存在，正在创建...")
            # 创建学习记录表
            session.execute(text("""
                CREATE TABLE IF NOT EXISTS learned_words (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    word VARCHAR(255) NOT NULL,
                    translate TEXT NOT NULL,
                    level VARCHAR(50),
                    source_table VARCHAR(50),
                    learn_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                    review_count INT DEFAULT 0,
                    last_review_time DATETIME NULL,
                    learn_stage INT DEFAULT 1 COMMENT '学习阶段：1=认识，2=填空，3=盲打，4=复习完成'
                )
            """))
            session.commit()
            print("已创建学习记录表 learned_words")
        
        print("成功连接到MySQL数据库")
        return True
        
    except Exception as e:
        print(f"连接到MySQL数据库失败: {e}")
        print("请确保MySQL数据库已启动并且配置正确")
        return False
    finally:
        session.close()

# 如果直接运行此文件，则初始化数据库
if __name__ == "__main__":
    init_database()
