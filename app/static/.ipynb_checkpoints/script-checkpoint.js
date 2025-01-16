let ws;
let mediaRecorder;
let audioChunks = [];

// WebSocket Bağlantısını Başlat
function connectWebSocket() {
    try {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.hostname}:8443/ws`;
        ws = new WebSocket(wsUrl);  // Global ws değişkenine atama yapıyoruz
        
        ws.onopen = () => {
            console.log('WebSocket bağlantısı kuruldu');
        };
        
        ws.onmessage = (event) => {
            const response = JSON.parse(event.data);
            displayMessage('Garson', response.text);
            if (response.order) {
                addOrder(response.order); // Gelen siparişleri listeye ekle
            }

            if (response.audio) {
                playAudio(response.audio);
            }
        };
        
        ws.onerror = (error) => {
            console.error('WebSocket hatası:', error);
            displayMessage('Sistem', 'Bağlantı hatası oluştu.');
        };

        ws.onclose = () => {
            console.log('WebSocket bağlantısı kapandı');
            setTimeout(connectWebSocket, 3000); // 3 saniye sonra yeniden bağlanmayı dene
        };
        
    } catch (error) {
        console.error('WebSocket bağlantı hatası:', error);
        displayMessage('Sistem', 'Bağlantı hatası. 3 saniye içinde yeniden denenecek.');
        setTimeout(connectWebSocket, 3000);
    }
}

let current_order = []; // Mevcut siparişler listesi

// Sipariş Ekleme ve Listeyi Güncelleme
function addOrder(order) {
    console.log('Sipariş ekleniyor:', order);
    current_order.push(order);
    console.log('Güncel sipariş listesi:', current_order);
    updateOrderList();
}

function updateOrderList() {
    const orderList = document.getElementById('orderList');
    orderList.innerHTML = ''; // Listeyi temizle
    current_order.forEach((order, index) => {
        const listItem = document.createElement('li');
        listItem.textContent = `${index + 1}. ${order}`;
        orderList.appendChild(listItem);
    });
}

// Siparişleri Kaydetme
function saveOrders() {
    if (current_order.length === 0) {
        displayMessage('Sistem', 'Kayıt edilecek sipariş yok!');
        return;
    }

    console.log('Siparişler kaydediliyor:', current_order); // Debug log
    displayMessage('Sistem', 'Siparişler başarıyla kaydedildi!');

    // Burada siparişleri sunucuya göndermek için bir işlem ekleyebilirsiniz.
    current_order = []; // Sipariş listesini sıfırla
    updateOrderList();
}



// Mesajı Sohbet Kutusuna Ekle
function displayMessage(sender, text) {
    const chatContainer = document.getElementById('chatContainer');
    const messageDiv = document.createElement('div');
    messageDiv.className = sender === 'User' ? 'user-message' : 'bot-message';
    messageDiv.textContent = `${sender}: ${text}`;
    chatContainer.appendChild(messageDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

// Ses Çalma
function playAudio(base64Audio) {
    const audio = new Audio(`data:audio/mp3;base64,${base64Audio}`);
    audio.play().catch(error => {
        console.error('Ses çalma hatası:', error);
    });
}

// Mikrofon Kaydını Başlat
async function startRecording() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);

        mediaRecorder.ondataavailable = (event) => {
            audioChunks.push(event.data);
        };

        mediaRecorder.onstop = async () => {
            const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
            audioChunks = [];
            await sendAudio(audioBlob);
        };

        mediaRecorder.start();
        toggleRecordingButtons(true);
    } catch (error) {
        console.error('Mikrofon erişim hatası:', error);
        displayMessage('Sistem', 'Mikrofona erişimde bir hata oluştu.');
    }
}

// Mikrofon Kaydını Durdur
function stopRecording() {
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
        mediaRecorder.stop();
        toggleRecordingButtons(false);
    }
}

// Ses Verisini Sunucuya Gönder
async function sendAudio(audioBlob) {
    const formData = new FormData();
    formData.append('audio', audioBlob, 'recording.wav');

    try {
        console.log('Sending audio to server...');  // Debug log
        const response = await fetch('https://localhost:8443/transcribe', {
            method: 'POST',
            body: formData
        });

        const contentType = response.headers.get('content-type');
        if (!response.ok) {
            const errorText = contentType && contentType.includes('application/json') 
                ? (await response.json()).detail 
                : await response.text();
            throw new Error(`Server Error (${response.status}): ${errorText}`);
        }

        const data = await response.json();
        console.log('Server response:', data);  // Debug log

        if (data.text) {
            displayMessage('User', data.text);
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({ type: 'voice', text: data.text }));
            }
        } else {
            throw new Error('No transcription text received');
        }
    } catch (error) {
        console.error('Ses dönüştürme hatası:', error);
        displayMessage('Sistem', `Ses dönüştürme hatası: ${error.message}`);
    }
}

// Mesaj Gönderme
function sendMessage() {
    console.log('sendMessage fonksiyonu çağrıldı');
    const input = document.getElementById('textInput');
    const text = input.value.trim();

    if (!text) {
        console.log('Boş mesaj');
        displayMessage('Sistem', 'Mesaj boş olamaz. Lütfen bir şey yazın.');
        return;
    }

    if (!ws || ws.readyState !== WebSocket.OPEN) {
        console.log('WebSocket bağlantısı yok veya kapalı, yeniden bağlanılıyor...');
        displayMessage('Sistem', 'Bağlantı kuruluyor, lütfen birkaç saniye bekleyin...');
        connectWebSocket();
        // Mesajı 1 saniye sonra tekrar göndermeyi dene
        setTimeout(() => {
            if (ws && ws.readyState === WebSocket.OPEN) {
                console.log('Yeniden bağlantı başarılı, mesaj gönderiliyor');
                displayMessage('User', text);
                ws.send(JSON.stringify({ type: 'text', text }));
                input.value = '';
            } else {
                displayMessage('Sistem', 'Bağlantı kurulamadı, lütfen sayfayı yenileyin.');
            }
        }, 1000);
        return;
    }

    console.log('Mesaj gönderiliyor:', text);
    displayMessage('User', text);
    ws.send(JSON.stringify({ type: 'text', text }));
    input.value = '';
}

// Event Listeners
function setupEventListeners() {
    console.log('Event listener\'lar ayarlanıyor');
    const sendButton = document.getElementById('sendButton');
    const textInput = document.getElementById('textInput');
    const startButton = document.getElementById('startButton');
    const stopButton = document.getElementById('stopButton');
    const saveOrdersButton = document.getElementById('saveOrdersButton');
    if (saveOrdersButton) {
        saveOrdersButton.onclick = saveOrders;
    }

    if (sendButton) {
        sendButton.onclick = sendMessage;  // addEventListener yerine doğrudan atama
        console.log('Send button event listener eklendi');
    }

    if (textInput) {
        textInput.onkeypress = (e) => {  // addEventListener yerine doğrudan atama
            if (e.key === 'Enter') {
                console.log('Enter tuşuna basıldı');
                sendMessage();
            }
        };
    }

    if (startButton) {
        startButton.onclick = startRecording;  // addEventListener yerine doğrudan atama
    }

    if (stopButton) {
        stopButton.onclick = stopRecording;  // addEventListener yerine doğrudan atama
    }
}

// Kayıt Düğmelerini Yönet
function toggleRecordingButtons(isRecording) {
    const startButton = document.getElementById('startButton');
    const stopButton = document.getElementById('stopButton');
    
    if (startButton && stopButton) {
        startButton.disabled = isRecording;
        stopButton.disabled = !isRecording;
    }
}

// Başlat
function init() {
    console.log('Uygulama başlatılıyor');
    connectWebSocket();
    setupEventListeners();
    
    // Sayfa kapatılırken WebSocket'i temiz bir şekilde kapat
    window.onbeforeunload = () => {
        if (ws) {
            ws.close();
        }
    };
}

// Sayfa Yüklendiğinde Başlat
document.addEventListener('DOMContentLoaded', init);