document.addEventListener('DOMContentLoaded', function() {
    // 获取DOM元素
    const wordWithBlanksElement = document.getElementById('word-with-blanks');
    const meaningElement = document.getElementById('meaning');
    const blanksContainer = document.getElementById('blanks-container');
    const submitButton = document.getElementById('submit-btn');
    const nextButton = document.getElementById('next-btn');
    const resultContainer = document.getElementById('result-container');
    const resultMessage = document.getElementById('result-message');
    const correctAnswer = document.getElementById('correct-answer');
    const correctCountElement = document.getElementById('correct-count');
    const wrongCountElement = document.getElementById('wrong-count');
    const messageContainer = document.getElementById('message-container') || createMessageContainer();
    
    // 统计数据
    let correctCount = 0;
    let wrongCount = 0;
    
    // 当前单词数据
    let currentWordWithBlanks = '';
    let currentWord = '';
    let numBlanks = 0;
    let currentBlanks = [];
    let blankPositions = [];  // 新增：存储空白的位置
    
    // 加载带空白的单词
    function loadWordWithBlanks() {
        // 清除之前的结果
        resultContainer.style.display = 'none';
        resultContainer.classList.remove('success', 'error');
        blanksContainer.innerHTML = '';
        
        // 显示加载提示
        wordWithBlanksElement.textContent = '正在加载...';
        meaningElement.textContent = '';
        
        fetch('/api/word-with-blanks')
            .then(response => {
                if (!response.ok) {
                    return response.json().then(data => {
                        throw new Error(data.message || '网络响应不正常');
                    });
                }
                return response.json();
            })
            .then(data => {
                if (!data.success) {
                    throw new Error(data.message || '获取单词失败');
                }
                
                currentWordWithBlanks = data.word_with_blanks;
                currentWord = data.word;  // 保存完整单词
                currentBlanks = data.blanks;  // 保存空白字符
                numBlanks = currentBlanks.length;
                
                // 计算空白的位置
                blankPositions = [];
                for (let i = 0; i < currentWordWithBlanks.length; i++) {
                    if (currentWordWithBlanks[i] === '_') {
                        blankPositions.push(i);
                    }
                }
                
                console.log('单词:', currentWord);
                console.log('带空白的单词:', currentWordWithBlanks);
                console.log('空白字符:', currentBlanks);
                console.log('空白位置:', blankPositions);
                
                // 显示带空白的单词
                wordWithBlanksElement.textContent = currentWordWithBlanks;
                meaningElement.textContent = data.meaning;
                
                // 创建填空输入框
                createBlankInputs(numBlanks);
            })
            .catch(error => {
                console.error('获取单词时出错:', error);
                wordWithBlanksElement.textContent = error.message || '加载失败';
                meaningElement.textContent = '请先在"认识单词"模块学习一些单词，然后再来练习填空。';
                blanksContainer.innerHTML = '<div class="alert alert-info">提示：您需要先完成单词认识阶段，才能进行填空练习。</div>';
            });
    }
    
    // 创建填空输入框
    function createBlankInputs(count) {
        blanksContainer.innerHTML = '';
        
        for (let i = 0; i < count; i++) {
            const input = document.createElement('input');
            input.type = 'text';
            input.className = 'blank-input';
            input.maxLength = 1;
            input.dataset.index = i;
            
            // 添加键盘事件，自动跳到下一个输入框
            input.addEventListener('keyup', function(event) {
                if (event.key === 'Enter') {
                    submitAnswer();
                } else if (this.value.length === this.maxLength) {
                    const nextInput = blanksContainer.querySelector(`input[data-index="${parseInt(this.dataset.index) + 1}"]`);
                    if (nextInput) {
                        nextInput.focus();
                    }
                }
            });
            
            blanksContainer.appendChild(input);
        }
        
        // 聚焦第一个输入框
        if (count > 0) {
            blanksContainer.querySelector('input[data-index="0"]').focus();
        }
    }
    
    // 创建消息容器
    function createMessageContainer() {
        const container = document.createElement('div');
        container.id = 'message-container';
        container.className = 'alert alert-success mt-3';
        container.style.display = 'none';
        container.style.position = 'fixed';
        container.style.bottom = '20px';
        container.style.right = '20px';
        container.style.zIndex = '1000';
        container.style.maxWidth = '300px';
        container.style.boxShadow = '0 4px 8px rgba(0,0,0,0.1)';
        document.body.appendChild(container);
        return container;
    }
    
    // 显示消息
    function showMessage(message, type = 'success', duration = 3000) {
        messageContainer.textContent = message;
        messageContainer.className = `alert alert-${type} mt-3`;
        messageContainer.style.display = 'block';
        
        // 自动隐藏消息
        setTimeout(() => {
            messageContainer.style.display = 'none';
        }, duration);
    }
    
    // 提交答案
    function submitAnswer() {
        const inputs = blanksContainer.querySelectorAll('.blank-input');
        const answers = Array.from(inputs).map(input => input.value.trim());
        
        // 检查是否所有空都已填写
        if (answers.some(answer => !answer)) {
            alert('请填写所有空格');
            return;
        }
        
        // 在前端验证答案
        let isCorrect = true;
        let incorrectIndexes = [];
        
        // 检查每个空格的答案是否正确
        for (let i = 0; i < answers.length; i++) {
            // 获取正确的字符
            const correctChar = currentBlanks[i];
            
            // 不区分大小写，并且忽略空格
            const userAnswer = answers[i].toLowerCase().trim();
            const correctAnswer = correctChar.toLowerCase().trim();
            
            console.log(`检查第${i}个空格: 用户输入="${userAnswer}", 正确答案="${correctAnswer}"`);
            
            if (userAnswer !== correctAnswer) {
                isCorrect = false;
                incorrectIndexes.push(i);
            }
        }
        
        // 高亮显示错误的输入框
        inputs.forEach((input, index) => {
            if (incorrectIndexes.includes(index)) {
                input.classList.add('error');
            } else {
                input.classList.remove('error');
            }
        });
        
        resultContainer.style.display = 'block';
        
        if (isCorrect) {
            resultContainer.classList.add('success');
            resultContainer.classList.remove('error');
            resultMessage.textContent = '回答正确！';
            correctCount++;
            correctCountElement.textContent = correctCount;
            
            // 显示学习成功消息
            showMessage(`单词 "${currentWord}" 填空练习完成！现在可以在"中文盲打"模块练习这个单词了。`, 'success', 5000);
            
            // 将单词标记为已完成第三阶段（填空）
            fetch('/api/update-word-stage', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ 
                    word: currentWord,
                    stage: 3  // 标记为已完成填空阶段
                })
            }).catch(error => {
                console.error('更新单词学习阶段时出错:', error);
            });
        } else {
            resultContainer.classList.add('error');
            resultContainer.classList.remove('success');
            resultMessage.textContent = '回答错误，请重试！';
            correctAnswer.textContent = `正确答案: ${currentWord}`;
            wrongCount++;
            wrongCountElement.textContent = wrongCount;
        }
    }
    
    // 事件监听
    submitButton.addEventListener('click', submitAnswer);
    nextButton.addEventListener('click', loadWordWithBlanks);
    
    // 页面加载时获取第一个单词
    loadWordWithBlanks();
});
