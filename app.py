from flask import Flask, render_template, request, jsonify, session, send_file
from flask_cors import CORS
import random
import os
import json
import init_db
from models import WordModel
from sqlalchemy import text
import tempfile
import requests

app = Flask(__name__)
CORS(app)  # 启用跨域支持
app.secret_key = os.urandom(24)  # 设置会话密钥

@app.route('/')
def index():
    """主页路由"""
    return render_template('index.html')

@app.route('/recognize')
def recognize_word():
    """认识单词页面"""
    return render_template('recognize.html')

@app.route('/filling')
def word_filling():
    """单词填空页面"""
    return render_template('filling.html')

@app.route('/typing')
def chinese_typing():
    """中文盲打页面"""
    return render_template('typing.html')

@app.route('/review')
def review_words():
    """复习单词页面"""
    return render_template('review.html')

@app.route('/api/levels')
def get_levels():
    """获取可用的单词级别"""
    levels = WordModel.get_available_levels()
    return jsonify({"levels": levels})

@app.route('/api/random-word', methods=['GET'])
def get_random_word():
    """获取随机单词API"""
    level = request.args.get('level', None)
    word = WordModel.get_random_word(level)
    if not word:
        return jsonify({"error": "没有找到单词"}), 404
    
    # 自动添加到学习记录，阶段为1（认识单词）
    WordModel.add_learned_word(word, stage=1)
    
    return jsonify(word)

@app.route('/api/word-with-blanks', methods=['GET'])
def get_word_with_blanks():
    """获取带空白的单词API"""
    num_blanks = request.args.get('blanks', None, type=int)
    
    # 获取第二阶段（填空）的单词，即从第一阶段（认识）中获取
    word = WordModel.get_words_by_stage(stage=2)
    
    if not word:
        # 如果没有找到第一阶段的单词，返回提示信息
        return jsonify({
            "success": False,
            "message": "您还没有学习过任何单词，请先在'认识单词'模块学习一些单词。"
        }), 404
    
    # 创建带空白的单词
    word_with_blanks, blanks = WordModel.create_word_with_blanks(word, num_blanks)
    
    if not word_with_blanks:
        return jsonify({"error": "创建带空白的单词失败"}), 500
    
    # 更新单词的学习阶段为2（填空）
    if 'id' in word:
        WordModel.update_word_stage(word['id'], 2)
    
    return jsonify({
        "success": True,
        "word": word["word"],
        "word_with_blanks": word_with_blanks,
        "blanks": blanks,
        "meaning": word["meaning"]
    })

@app.route('/api/typing-word', methods=['GET'])
def get_typing_word():
    """获取中文盲打单词API"""
    # 获取第三阶段（盲打）的单词，即从第二阶段（填空）中获取
    word = WordModel.get_words_by_stage(stage=3)
    
    if not word:
        # 如果没有找到第二阶段的单词，返回提示信息
        return jsonify({
            "success": False,
            "message": "您还没有在'单词填空'模块学习过任何单词，请先完成一些填空练习。"
        }), 404
    
    # 更新单词的学习阶段为3（盲打）
    if 'id' in word:
        WordModel.update_word_stage(word['id'], 3)
    
    return jsonify({
        "success": True,
        "word": word["word"],
        "meaning": word["meaning"]
    })

@app.route('/api/check-blanks', methods=['POST'])
def check_blanks():
    """检查填空答案API"""
    data = request.json
    user_answers = data.get('answers', [])
    
    # 从会话获取正确答案
    correct_blanks = session.get('current_blanks', [])
    current_word = session.get('current_word', '')
    current_level = session.get('current_level', '默认')
    
    if not correct_blanks or len(user_answers) != len(correct_blanks):
        return jsonify({"error": "无效的答案"}), 400
    
    # 检查答案
    is_correct = all(user_answer.lower() == correct_blank.lower() 
                    for user_answer, correct_blank in zip(user_answers, correct_blanks))
    
    return jsonify({
        "is_correct": is_correct,
        "correct_word": current_word,
        "correct_blanks": correct_blanks,
        "level": current_level
    })

@app.route('/api/random-meaning')
def get_random_meaning():
    """获取随机中文释义API"""
    level = request.args.get('level', None)
    word = WordModel.get_random_word(level)
    if not word:
        return jsonify({"error": "没有找到单词"}), 404
    
    # 保存正确答案到会话
    if 'id' in word:
        session['current_word_id'] = word['id']
    session['current_word'] = word['word']
    session['current_level'] = word.get('level', '默认')
    
    return jsonify({
        "meaning": word['meaning'],
        "level": word.get('level', '默认')
    })

@app.route('/api/check-typing', methods=['POST'])
def check_typing():
    """检查中文盲打答案API"""
    data = request.json
    user_answer = data.get('answer', '').strip().lower()
    
    # 从会话获取正确答案
    current_word = session.get('current_word', '').lower()
    current_level = session.get('current_level', '默认')
    
    if not current_word:
        return jsonify({"error": "无效的会话"}), 400
    
    # 检查答案
    is_correct = user_answer == current_word
    
    return jsonify({
        "is_correct": is_correct,
        "correct_word": current_word,
        "level": current_level
    })

@app.route('/api/reset-words', methods=['POST'])
def reset_words():
    """重置已显示的单词记录"""
    result = WordModel.reset_shown_words()
    return jsonify(result)

@app.route('/api/learned-words', methods=['GET'])
def get_learned_words():
    """获取学习记录API"""
    limit = request.args.get('limit', 50, type=int)
    offset = request.args.get('offset', 0, type=int)
    sort_by = request.args.get('sort_by', 'learn_time')
    sort_order = request.args.get('sort_order', 'desc')
    
    result = WordModel.get_learned_words(limit, offset, sort_by, sort_order)
    return jsonify(result)

@app.route('/api/learned-word/<int:word_id>', methods=['DELETE'])
def delete_learned_word(word_id):
    """删除学习记录API"""
    result = WordModel.delete_learned_word(word_id)
    return jsonify(result)

@app.route('/api/learned-words/clear', methods=['DELETE'])
def clear_learned_words():
    """清空学习记录API"""
    result = WordModel.clear_learned_words()
    return jsonify(result)

@app.route('/api/learned-word', methods=['POST'])
def add_learned_word():
    """手动添加学习记录API"""
    data = request.get_json()
    
    if not data or 'word' not in data or 'meaning' not in data:
        return jsonify({"error": "缺少必要参数"}), 400
    
    word_dict = {
        "word": data['word'],
        "meaning": data['meaning'],
        "level": data.get('level', "未知"),
        "source_table": data.get('source_table')
    }
    
    result = WordModel.add_learned_word(word_dict)
    return jsonify(result)

@app.route('/api/update-word-stage', methods=['POST'])
def update_word_stage():
    """更新单词的学习阶段"""
    data = request.json
    if not data or 'word' not in data or 'stage' not in data:
        return jsonify({"success": False, "message": "缺少必要参数"}), 400
    
    word = data['word']
    stage = data['stage']
    
    # 查询单词ID
    query = text("SELECT id FROM learned_words WHERE word = :word")
    result = init_db.session.execute(query, {"word": word}).fetchone()
    
    if result:
        word_id = result[0]
        # 更新单词的学习阶段
        response = WordModel.update_word_stage(word_id, stage)
        return jsonify(response)
    else:
        return jsonify({"success": False, "message": "未找到该单词"}), 404

@app.route('/api/text-to-speech', methods=['GET'])
def text_to_speech():
    """文本转语音API"""
    text = request.args.get('text', '')
    if not text:
        return jsonify({"error": "未提供文本"}), 400
    
    try:
        # 使用免费的Voicerss TTS API
        api_key = "c6c9f5b5c8f34d7b8e5a3c7d9b8a7c5d"  # 这是一个示例密钥，实际使用时请替换为您自己的密钥
        url = f"https://api.voicerss.org/?key={api_key}&hl=en-us&v=Amy&c=MP3&f=16khz_16bit_stereo&src={text}"
        
        # 创建临时文件保存音频
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
        temp_file_path = temp_file.name
        temp_file.close()
        
        # 下载音频文件
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            with open(temp_file_path, 'wb') as f:
                f.write(response.content)
            
            # 发送音频文件
            return send_file(temp_file_path, mimetype='audio/mpeg')
        else:
            return jsonify({"error": f"获取音频失败，状态码: {response.status_code}"}), 500
    
    except Exception as e:
        return jsonify({"error": f"生成语音出错: {str(e)}"}), 500
    
    finally:
        # 确保临时文件被删除
        if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except:
                pass

@app.route('/status')
def status():
    """应用状态API"""
    if init_db.use_in_memory:
        mode = "内存模式"
        tables = []
    else:
        mode = "MySQL模式"
        tables = list(init_db.VOCABULARY_TABLES.items())
    
    return jsonify({
        "status": "running",
        "database_mode": mode,
        "vocabulary_tables": tables
    })

if __name__ == '__main__':
    init_db.init_database()
    app.run(debug=True, host='0.0.0.0', port=5000)
