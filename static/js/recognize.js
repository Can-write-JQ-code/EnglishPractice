document.addEventListener('DOMContentLoaded', function() {
    // 获取DOM元素
    const wordElement = document.getElementById('word');
    const meaningElement = document.getElementById('meaning');
    const playButton = document.getElementById('play-btn');
    const nextButton = document.getElementById('next-btn');
    const autoSwitch = document.getElementById('auto-switch');
    const messageContainer = document.getElementById('message-container') || createMessageContainer();
    const audioElement = document.getElementById('word-audio') || document.createElement('audio');
    audioElement.id = 'word-audio';
    document.body.appendChild(audioElement);
    
    // 当前单词数据
    let currentWord = null;
    
    // 自动切换定时器
    let autoSwitchTimer = null;
    const autoSwitchInterval = 5000; // 5秒
    
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
    
    // 加载随机单词
    function loadRandomWord() {
        fetch('/api/random-word')
            .then(response => {
                if (!response.ok) {
                    throw new Error('网络响应不正常');
                }
                return response.json();
            })
            .then(data => {
                currentWord = data;
                wordElement.textContent = data.word;
                meaningElement.textContent = data.meaning;
                
                // 显示学习成功消息
                showMessage(`单词 "${data.word}" 已添加到学习记录！现在可以在"单词填空"模块练习这个单词了。`, 'success', 5000);
            })
            .catch(error => {
                console.error('获取单词时出错:', error);
                wordElement.textContent = '加载失败';
                meaningElement.textContent = '请检查网络连接或刷新页面';
            });
    }
    
    // 朗读当前单词
    function speakWord() {
        if (!currentWord) return;
        
        // 显示加载提示
        playButton.textContent = '加载中...';
        playButton.disabled = true;
        
        // 获取音频元素
        const audioElement = document.getElementById('word-audio');
        
        // 设置音频源为免费的TTS服务
        const ttsUrl = `https://audio.oxforddictionaries.com/en/mp3/${currentWord.word}__us_1.mp3`;
        audioElement.src = ttsUrl;
        
        // 播放成功
        audioElement.onloadeddata = function() {
            audioElement.play();
            playButton.textContent = '朗读';
            playButton.disabled = false;
        };
        
        // 播放失败时尝试备选方案
        audioElement.onerror = function() {
            console.log('Oxford发音加载失败，尝试备选方案');
            
            // 尝试使用另一个免费的TTS服务
            const backupUrl = `https://dict.youdao.com/dictvoice?audio=${currentWord.word}&type=2`;
            audioElement.src = backupUrl;
            
            audioElement.onloadeddata = function() {
                audioElement.play();
                playButton.textContent = '朗读';
                playButton.disabled = false;
            };
            
            // 如果备选方案也失败
            audioElement.onerror = function() {
                console.log('有道发音加载失败，尝试浏览器内置TTS');
                playButton.textContent = '朗读';
                playButton.disabled = false;
                
                // 尝试使用浏览器内置的语音合成API
                if ('speechSynthesis' in window) {
                    const utterance = new SpeechSynthesisUtterance(currentWord.word);
                    utterance.lang = 'en-US';
                    speechSynthesis.speak(utterance);
                } else {
                    showMessage('无法朗读单词，请检查网络连接', 'warning');
                }
            };
        };
    }
    
    // 启动自动切换
    function startAutoSwitch() {
        if (autoSwitchTimer) {
            clearInterval(autoSwitchTimer);
        }
        
        autoSwitchTimer = setInterval(() => {
            loadRandomWord();
        }, autoSwitchInterval);
    }
    
    // 停止自动切换
    function stopAutoSwitch() {
        if (autoSwitchTimer) {
            clearInterval(autoSwitchTimer);
            autoSwitchTimer = null;
        }
    }
    
    // 事件监听
    nextButton.addEventListener('click', loadRandomWord);
    
    playButton.addEventListener('click', speakWord);
    
    autoSwitch.addEventListener('change', function() {
        if (this.checked) {
            startAutoSwitch();
        } else {
            stopAutoSwitch();
        }
    });
    
    // 页面加载时获取第一个单词
    loadRandomWord();
    
    // 页面卸载时清除定时器
    window.addEventListener('beforeunload', function() {
        stopAutoSwitch();
    });
});
