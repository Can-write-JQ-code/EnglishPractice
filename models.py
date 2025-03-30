import random
import os
import collections
import datetime
from dotenv import load_dotenv
from sqlalchemy import text
import init_db
from init_db import in_memory_words, VOCABULARY_TABLES, MEMORY_LEVELS, LearnedWord

# 加载环境变量
load_dotenv()

# 用于记录最近显示过的单词，避免短期内重复
recent_words = collections.deque(maxlen=50)
# 记录每个级别的单词总数（用于内存模式）
level_word_counts = {}
# 记录每个表的单词总数（用于数据库模式）
table_word_counts = {}

class WordModel:
    @staticmethod
    def get_available_levels():
        """获取可用的单词级别"""
        if init_db.use_in_memory:
            return MEMORY_LEVELS
        else:
            try:
                return list(VOCABULARY_TABLES.values())
            except Exception as e:
                print(f"获取单词级别时出错: {e}")
                return []
    
    @staticmethod
    def _count_words_by_level():
        """统计每个级别的单词数量（内存模式）"""
        global level_word_counts
        if not level_word_counts:
            level_word_counts = {}
            for level in MEMORY_LEVELS:
                level_word_counts[level] = len([word for word in in_memory_words if word.get("level") == level])
        return level_word_counts
    
    @staticmethod
    def _count_words_by_table():
        """统计每个表的单词数量（数据库模式）"""
        global table_word_counts
        if not table_word_counts:
            table_word_counts = {}
            try:
                for table_name in VOCABULARY_TABLES.keys():
                    count_query = text(f"SELECT COUNT(*) FROM {table_name}")
                    count = init_db.session.execute(count_query).scalar()
                    table_word_counts[table_name] = count
            except Exception as e:
                print(f"统计表单词数量时出错: {e}")
        return table_word_counts
    
    @staticmethod
    def get_random_word(level=None):
        """获取随机单词，可以指定级别，避免短期内重复"""
        global recent_words
        
        if init_db.use_in_memory:
            # 由于我们已经注释掉了回退逻辑，这部分代码不应该被执行
            print("错误：系统被配置为只使用MySQL数据库，但尝试使用内存模式")
            return None
        else:
            try:
                # 确定要查询的表
                table_name = None
                if level:
                    # 根据中文级别名称找到对应的表名
                    for table, level_name in VOCABULARY_TABLES.items():
                        if level_name == level:
                            table_name = table
                            break
                
                if not table_name:
                    # 如果没有指定级别或找不到对应的表，随机选择一个表
                    table_name = random.choice(list(VOCABULARY_TABLES.keys()))
                
                # 获取表中的记录数
                table_counts = WordModel._count_words_by_table()
                count = table_counts.get(table_name, 0)
                
                if count == 0:
                    count_query = text(f"SELECT COUNT(*) FROM {table_name}")
                    count = init_db.session.execute(count_query).scalar()
                    table_counts[table_name] = count
                
                if count == 0:
                    return None
                
                # 如果最近显示的单词数量已经接近该表的总单词数，清空记录
                if len(recent_words) > count * 0.7:
                    recent_words.clear()
                    print(f"已重置单词记录，当前表: {table_name}，总单词数: {count}")
                
                # 尝试最多20次获取未在最近显示过的单词
                for _ in range(min(20, count)):
                    # 使用ORDER BY RAND()方法获取真正随机的单词
                    word_query = text(f"SELECT word, translate as meaning FROM {table_name} ORDER BY RAND() LIMIT 1")
                    result = init_db.session.execute(word_query).fetchone()
                    
                    if result and result[0] not in recent_words:
                        # 将结果转换为字典
                        word_dict = {
                            "word": result[0],
                            "meaning": result[1],
                            "level": VOCABULARY_TABLES.get(table_name, "未知"),
                            "source_table": table_name
                        }
                        recent_words.append(result[0])
                        print(f"获取到新单词(SQL): {result[0]}，当前记录数: {len(recent_words)}")
                        return word_dict
                
                # 如果多次尝试都失败，重置记录并再次尝试
                recent_words.clear()
                
                # 再次随机获取一个单词
                word_query = text(f"SELECT word, translate as meaning FROM {table_name} ORDER BY RAND() LIMIT 1")
                result = init_db.session.execute(word_query).fetchone()
                
                if result:
                    # 将结果转换为字典
                    word_dict = {
                        "word": result[0],
                        "meaning": result[1],
                        "level": VOCABULARY_TABLES.get(table_name, "未知"),
                        "source_table": table_name
                    }
                    recent_words.append(result[0])
                    print(f"重置记录后获取到单词(SQL): {result[0]}")
                    return word_dict
                return None
            except Exception as e:
                print(f"获取随机单词时出错: {e}")
                return None
    
    @staticmethod
    def get_word_by_text(word_text, level=None):
        """根据单词文本获取单词"""
        if init_db.use_in_memory:
            # 由于我们已经注释掉了回退逻辑，这部分代码不应该被执行
            print("错误：系统被配置为只使用MySQL数据库，但尝试使用内存模式")
            return None
        else:
            try:
                # 确定要查询的表
                tables_to_search = []
                if level:
                    # 根据中文级别名称找到对应的表名
                    for table, level_name in VOCABULARY_TABLES.items():
                        if level_name == level:
                            tables_to_search.append(table)
                            break
                else:
                    # 如果没有指定级别，搜索所有表
                    tables_to_search = list(VOCABULARY_TABLES.keys())
                
                # 在指定的表中查找单词
                for table_name in tables_to_search:
                    word_query = text(f"SELECT word, translate as meaning FROM {table_name} WHERE word = :word")
                    result = init_db.session.execute(word_query, {"word": word_text}).fetchone()
                    
                    if result:
                        # 将结果转换为字典
                        word_dict = {
                            "word": result[0],
                            "meaning": result[1],
                            "level": VOCABULARY_TABLES.get(table_name, "未知"),
                            "source_table": table_name
                        }
                        return word_dict
                
                return None
            except Exception as e:
                print(f"根据文本获取单词时出错: {e}")
                return None
    
    @staticmethod
    def get_word_by_meaning(meaning, level=None):
        """根据中文释义获取单词"""
        if init_db.use_in_memory:
            # 由于我们已经注释掉了回退逻辑，这部分代码不应该被执行
            print("错误：系统被配置为只使用MySQL数据库，但尝试使用内存模式")
            return None
        else:
            try:
                # 确定要查询的表
                tables_to_search = []
                if level:
                    # 根据中文级别名称找到对应的表名
                    for table, level_name in VOCABULARY_TABLES.items():
                        if level_name == level:
                            tables_to_search.append(table)
                            break
                else:
                    # 如果没有指定级别，搜索所有表
                    tables_to_search = list(VOCABULARY_TABLES.keys())
                
                # 在指定的表中查找单词
                for table_name in tables_to_search:
                    word_query = text(f"SELECT word, translate as meaning FROM {table_name} WHERE translate LIKE :meaning")
                    result = init_db.session.execute(word_query, {"meaning": f"%{meaning}%"}).fetchone()
                    
                    if result:
                        # 将结果转换为字典
                        word_dict = {
                            "word": result[0],
                            "meaning": result[1],
                            "level": VOCABULARY_TABLES.get(table_name, "未知"),
                            "source_table": table_name
                        }
                        return word_dict
                
                return None
            except Exception as e:
                print(f"根据释义获取单词时出错: {e}")
                return None
    
    @staticmethod
    def reset_shown_words():
        """重置已显示单词的记录"""
        global recent_words, level_word_counts, table_word_counts
        recent_words.clear()
        level_word_counts = {}
        table_word_counts = {}
        return {"success": True, "message": "已重置单词记录"}
    
    @staticmethod
    def create_word_with_blanks(word, num_blanks=None):
        """创建带有空白的单词，返回带空白的单词和正确答案"""
        if not word:
            return None, None
            
        word_text = word["word"]
        word_length = len(word_text)
        
        # 如果未指定空白数量，则根据单词长度决定
        if num_blanks is None:
            num_blanks = max(1, min(3, word_length // 3))
        
        # 确保空白数量不超过单词长度
        num_blanks = min(num_blanks, word_length)
        
        # 随机选择要挖空的位置
        blank_positions = random.sample(range(word_length), num_blanks)
        blank_positions.sort()  # 确保位置有序
        
        # 创建带空白的单词
        word_with_blanks = list(word_text)
        blanks = []
        
        for pos in blank_positions:
            blanks.append(word_text[pos])
            word_with_blanks[pos] = '_'
        
        return ''.join(word_with_blanks), blanks
    
    @staticmethod
    def add_learned_word(word_dict, stage=1):
        """添加学习过的单词到学习记录表"""
        try:
            # 检查单词是否已经存在于学习记录表中
            query = text("SELECT id, review_count, learn_stage FROM learned_words WHERE word = :word")
            result = init_db.session.execute(query, {"word": word_dict["word"]}).fetchone()
            
            if result:
                # 如果单词已存在，更新复习次数、最后复习时间和学习阶段
                word_id, review_count, current_stage = result
                
                # 如果传入的学习阶段大于当前阶段，则更新学习阶段
                new_stage = max(stage, current_stage)
                
                update_query = text("""
                    UPDATE learned_words 
                    SET review_count = :review_count, 
                        last_review_time = :review_time,
                        learn_stage = :learn_stage
                    WHERE id = :id
                """)
                init_db.session.execute(update_query, {
                    "review_count": review_count + 1,
                    "review_time": datetime.datetime.now(),
                    "learn_stage": new_stage,
                    "id": word_id
                })
                init_db.session.commit()
                return {"success": True, "message": "已更新学习记录", "review_count": review_count + 1, "stage": new_stage}
            else:
                # 如果单词不存在，创建新记录
                learned_word = LearnedWord(
                    word=word_dict["word"],
                    translate=word_dict["meaning"],
                    level=word_dict.get("level", "未知"),
                    source_table=word_dict.get("source_table", None),
                    learn_time=datetime.datetime.now(),
                    review_count=1,
                    last_review_time=datetime.datetime.now(),
                    learn_stage=stage
                )
                init_db.session.add(learned_word)
                init_db.session.commit()
                return {"success": True, "message": "已添加到学习记录", "review_count": 1, "stage": stage}
        except Exception as e:
            init_db.session.rollback()
            print(f"添加学习记录时出错: {e}")
            return {"success": False, "message": f"添加学习记录失败: {e}"}
    
    @staticmethod
    def get_learned_words(limit=50, offset=0, sort_by="learn_time", sort_order="desc"):
        """获取学习记录列表"""
        try:
            # 构建排序条件
            sort_column = "learn_time"
            if sort_by in ["learn_time", "review_count", "last_review_time", "word"]:
                sort_column = sort_by
            
            order_direction = "DESC"
            if sort_order.lower() == "asc":
                order_direction = "ASC"
            
            # 查询学习记录
            query = text(f"""
                SELECT id, word, translate, level, source_table, 
                       learn_time, review_count, last_review_time, learn_stage
                FROM learned_words 
                ORDER BY {sort_column} {order_direction}
                LIMIT :limit OFFSET :offset
            """)
            
            results = init_db.session.execute(query, {"limit": limit, "offset": offset}).fetchall()
            
            # 获取总记录数
            count_query = text("SELECT COUNT(*) FROM learned_words")
            total_count = init_db.session.execute(count_query).scalar()
            
            # 转换结果为字典列表
            words = []
            for row in results:
                words.append({
                    "id": row[0],
                    "word": row[1],
                    "meaning": row[2],
                    "level": row[3],
                    "source_table": row[4],
                    "learn_time": row[5].strftime("%Y-%m-%d %H:%M:%S") if row[5] else None,
                    "review_count": row[6],
                    "last_review_time": row[7].strftime("%Y-%m-%d %H:%M:%S") if row[7] else None,
                    "learn_stage": row[8]
                })
            
            return {
                "success": True,
                "total": total_count,
                "offset": offset,
                "limit": limit,
                "words": words
            }
        except Exception as e:
            print(f"获取学习记录时出错: {e}")
            return {"success": False, "message": f"获取学习记录失败: {e}"}
    
    @staticmethod
    def get_words_by_stage(stage, limit=1, exclude_ids=None):
        """根据学习阶段获取单词"""
        try:
            # 如果是第一阶段（认识单词），则随机获取一个单词
            if stage == 1:
                return WordModel.get_random_word()
            
            # 构建查询条件
            conditions = [f"learn_stage >= {stage - 1}"]  # 获取上一阶段或更高阶段的单词
            
            # 如果有需要排除的单词ID，添加到条件中
            if exclude_ids and len(exclude_ids) > 0:
                ids_str = ",".join([str(id) for id in exclude_ids])
                conditions.append(f"id NOT IN ({ids_str})")
            
            # 构建完整的查询语句
            where_clause = " AND ".join(conditions)
            query = text(f"""
                SELECT id, word, translate, level, source_table, learn_stage
                FROM learned_words 
                WHERE {where_clause}
                ORDER BY RAND()
                LIMIT :limit
            """)
            
            results = init_db.session.execute(query, {"limit": limit}).fetchall()
            
            # 如果没有找到符合条件的单词，返回None
            if not results:
                return None
            
            # 转换结果为字典
            words = []
            for row in results:
                words.append({
                    "id": row[0],
                    "word": row[1],
                    "meaning": row[2],
                    "level": row[3],
                    "source_table": row[4],
                    "learn_stage": row[5]
                })
            
            # 如果只需要一个单词，直接返回第一个
            if limit == 1:
                return words[0]
            
            return words
            
        except Exception as e:
            print(f"根据学习阶段获取单词时出错: {e}")
            return None
    
    @staticmethod
    def update_word_stage(word_id, stage):
        """更新单词的学习阶段"""
        try:
            query = text("""
                UPDATE learned_words 
                SET learn_stage = :stage,
                    last_review_time = :review_time
                WHERE id = :id
            """)
            init_db.session.execute(query, {
                "stage": stage,
                "review_time": datetime.datetime.now(),
                "id": word_id
            })
            init_db.session.commit()
            return {"success": True, "message": "已更新学习阶段"}
        except Exception as e:
            init_db.session.rollback()
            print(f"更新学习阶段时出错: {e}")
            return {"success": False, "message": f"更新学习阶段失败: {e}"}
    
    @staticmethod
    def delete_learned_word(word_id):
        """删除学习记录"""
        try:
            query = text("DELETE FROM learned_words WHERE id = :id")
            init_db.session.execute(query, {"id": word_id})
            init_db.session.commit()
            return {"success": True, "message": "已删除学习记录"}
        except Exception as e:
            init_db.session.rollback()
            print(f"删除学习记录时出错: {e}")
            return {"success": False, "message": f"删除学习记录失败: {e}"}
    
    @staticmethod
    def clear_learned_words():
        """清空所有学习记录"""
        try:
            query = text("DELETE FROM learned_words")
            init_db.session.execute(query)
            init_db.session.commit()
            return {"success": True, "message": "已清空所有学习记录"}
        except Exception as e:
            init_db.session.rollback()
            print(f"清空学习记录时出错: {e}")
            return {"success": False, "message": f"清空学习记录失败: {e}"}
