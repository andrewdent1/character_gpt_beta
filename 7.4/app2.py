from flask import Flask, request, jsonify, render_template
import os
import requests
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'

# Ensure the upload folder exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# Define your API keys and endpoints
openai_api_key = "-"
elevenlabs_api_key "-"
whisper_api_key = "-"

# Define the OpenAI endpoint
openai_url = "https://api.openai.com/v1/chat/completions"

# Define the Eleven Labs endpoint for text-to-speech
elevenlabs_url = "https://api.elevenlabs.io/v1/text-to-speech/"

# Define the Whisper AI endpoint for transcription
whisper_url = "https://api.openai.ai/v1/transcriptions"

# Function to get chatbot response from OpenAI
def get_chatbot_response(prompt):
    openai_headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {openai_api_key}"
    }
    openai_payload = {
        "model": "gpt-4",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 150
    }
    response = requests.post(openai_url, headers=openai_headers, json=openai_payload)
    
    if response.status_code != 200:
        print(f"Error: Received status code {response.status_code}")
        print(f"Response: {response.text}")
        return "Sorry, I couldn't generate a response."

    response_json = response.json()
    
    if 'choices' not in response_json or len(response_json['choices']) == 0:
        print("Error: Unexpected response format")
        print(f"Response JSON: {response_json}")
        return "Sorry, I couldn't generate a response."

    return response_json['choices'][0]['message']['content'].strip()

# Function to convert text to speech using Eleven Labs
def text_to_speech_elevenlabs(text, voice_id):
    elevenlabs_headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": elevenlabs_api_key
    }
    elevenlabs_payload = {
        "text": text,
        "model_id": "eleven_monolingual_v1",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.5
        }
    }
    response = requests.post(f"{elevenlabs_url}{voice_id}", json=elevenlabs_payload, headers=elevenlabs_headers)
    
    if response.status_code != 200:
        print(f"Error: Received status code {response.status_code}")
        print(f"Response: {response.text}")
        return None

    output_file = "static/output.mp3"
    with open(output_file, 'wb') as f:
        for chunk in response.iter_content(chunk_size=1024):
            if chunk:
                f.write(chunk)

    return output_file

# Function to transcribe audio using Whisper AI
def transcribe_audio_whisper(file_path):
    whisper_headers = {
        "Authorization": f"Bearer {openai_api_key}"
    }
    files = {'file': open(file_path, 'rb')}
    data = {'model': 'whisper-1'}
    
    response = requests.post(openai_url, headers=whisper_headers, files=files, data=data)
    
    if response.status_code != 200:
        print(f"Error: Received status code {response.status_code}")
        print(f"Response: {response.text}")
        return None

    response_json = response.json()
    return response_json.get("text")

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/chatbot')
def chatbot():
    return render_template('chatbot.html')

@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    user_input = data.get('user_input')
    voice_id = data.get('voice_id', '0UmLVoOMMM6fxQsAVmyY')  # Default voice ID if not provided
    chatbot_response = get_chatbot_response(user_input)
    audio_file = text_to_speech_elevenlabs(chatbot_response, voice_id)
    if audio_file:
        return jsonify({"response": chatbot_response, "audio_url": audio_file})
    else:
        return jsonify({"error": "Sorry, I couldn't convert the response to audio."}), 500

@app.route('/process_audio', methods=['POST'])
def process_audio():
    if 'audio' not in request.files:
        return jsonify({"error": "No audio file provided."}), 400
    
    audio_file = request.files['audio']
    if audio_file.filename == '':
        return jsonify({"error": "No selected file."}), 400

    filename = secure_filename(audio_file.filename)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    audio_file.save(file_path)

    transcribed_text = transcribe_audio_whisper(file_path)
    if not transcribed_text:
        return jsonify({"error": "Failed to transcribe audio."}), 500

    chatbot_response = get_chatbot_response(transcribed_text)
    audio_file = text_to_speech_elevenlabs(chatbot_response, '0UmLVoOMMM6fxQsAVmyY')
    if audio_file:
        return jsonify({"response": chatbot_response, "audio_url": audio_file})
    else:
        return jsonify({"error": "Sorry, I couldn't convert the response to audio."}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
