document.addEventListener('DOMContentLoaded', function() {
    // 获取DOM元素
    const meaningElement = document.getElementById('meaning');
    const answerInput = document.getElementById('answer-input');
    const submitButton = document.getElementById('submit-btn');
    const nextButton = document.getElementById('next-btn');
    const timerSwitch = document.getElementById('timer-switch');
    const timerDisplay = document.getElementById('timer-display');
    const resultContainer = document.getElementById('result-container');
    const resultMessage = document.getElementById('result-message');
    const correctAnswer = document.getElementById('correct-answer');
    const correctCountElement = document.getElementById('correct-count');
    const wrongCountElement = document.getElementById('wrong-count');
    const messageContainer = document.getElementById('message-container') || createMessageContainer();
    
    // 统计数据
    let correctCount = 0;
    let wrongCount = 0;
    
    // 当前单词
    let currentWord = '';
    
    // 计时器相关
    let timerInterval = null;
    let timeLeft = 30; // 默认30秒
    const defaultTime = 30;
    
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
    
    // 加载随机中文释义
    function loadRandomMeaning() {
        // 清除之前的结果和输入
        resultContainer.style.display = 'none';
        resultContainer.classList.remove('success', 'error');
        answerInput.value = '';
        answerInput.disabled = false;
        
        // 重置计时器
        resetTimer();
        
        // 显示加载提示
        meaningElement.textContent = '正在加载...';
        
        fetch('/api/typing-word')
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
                
                meaningElement.textContent = data.meaning;
                currentWord = data.word;  // 保存当前单词
                answerInput.focus();
                
                // 如果启用了限时模式，开始计时
                if (timerSwitch.checked) {
                    startTimer();
                }
            })
            .catch(error => {
                console.error('获取中文释义时出错:', error);
                meaningElement.textContent = error.message || '加载失败';
                answerInput.disabled = true;
                
                // 显示友好的提示信息
                resultContainer.style.display = 'block';
                resultContainer.classList.add('info');
                resultContainer.classList.remove('success', 'error');
                resultMessage.textContent = '提示：您需要先完成单词填空阶段，才能进行中文盲打练习。';
                correctAnswer.textContent = '请先在"单词填空"模块学习一些单词，然后再来练习盲打。';
            });
    }
    
    // 提交答案
    function submitAnswer() {
        const userAnswer = answerInput.value.trim();
        
        if (!userAnswer) {
            alert('请输入答案');
            return;
        }
        
        // 停止计时器
        stopTimer();
        
        // 显示结果
        resultContainer.style.display = 'block';
        answerInput.disabled = true;
        
        // 检查答案
        if (userAnswer.toLowerCase() === currentWord.toLowerCase()) {
            resultContainer.classList.add('success');
            resultContainer.classList.remove('error');
            resultMessage.textContent = '回答正确！';
            correctAnswer.textContent = '';
            correctCount++;
            correctCountElement.textContent = correctCount;
            
            // 显示学习成功消息
            showMessage(`单词 "${currentWord}" 盲打练习完成！恭喜您已完成该单词的所有学习阶段，可以在"复习"模块查看。`, 'success', 5000);
            
            // 将单词标记为已完成第四阶段（复习完成）
            fetch('/api/update-word-stage', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ 
                    word: currentWord,
                    stage: 4  // 标记为已完成所有学习阶段
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
    
    // 开始计时器
    function startTimer() {
        timeLeft = defaultTime;
        updateTimerDisplay();
        
        timerInterval = setInterval(() => {
            timeLeft--;
            updateTimerDisplay();
            
            if (timeLeft <= 0) {
                timeOut();
            }
        }, 1000);
    }
    
    // 停止计时器
    function stopTimer() {
        if (timerInterval) {
            clearInterval(timerInterval);
            timerInterval = null;
        }
    }
    
    // 重置计时器
    function resetTimer() {
        stopTimer();
        timeLeft = defaultTime;
        updateTimerDisplay();
    }
    
    // 更新计时器显示
    function updateTimerDisplay() {
        timerDisplay.textContent = `${timeLeft}s`;
        
        // 当时间不足10秒时，添加警告样式
        if (timeLeft <= 10) {
            timerDisplay.style.color = 'red';
        } else {
            timerDisplay.style.color = '';
        }
    }
    
    // 时间到
    function timeOut() {
        stopTimer();
        answerInput.disabled = true;
        
        // 获取正确答案
        fetch('/api/check-typing', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ answer: '' }) // 发送空答案，服务器会返回正确答案
        })
        .then(response => response.json())
        .then(data => {
            resultContainer.style.display = 'block';
            resultContainer.classList.add('error');
            resultContainer.classList.remove('success');
            resultMessage.textContent = '时间到！';
            correctAnswer.textContent = `正确答案: ${data.correct_word}`;
            wrongCount++;
            wrongCountElement.textContent = wrongCount;
        });
    }
    
    // 事件监听
    submitButton.addEventListener('click', submitAnswer);
    nextButton.addEventListener('click', loadRandomMeaning);
    
    // 回车键提交
    answerInput.addEventListener('keyup', function(event) {
        if (event.key === 'Enter') {
            submitAnswer();
        }
    });
    
    // 计时器开关
    timerSwitch.addEventListener('change', function() {
        if (this.checked) {
            startTimer();
        } else {
            stopTimer();
        }
    });
    
    // 页面加载时获取第一个中文释义
    loadRandomMeaning();
    
    // 页面卸载时清除计时器
    window.addEventListener('beforeunload', function() {
        stopTimer();
    });
});
