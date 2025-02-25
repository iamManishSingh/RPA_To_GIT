
python
Copy
# --------------------------
# backend/config.py
# --------------------------
import os

class Config:
    AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
    AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
    AZURE_OPENAI_API_VERSION = "2023-05-15"
    AZURE_DEPLOYMENT_NAME = "gpt-4"
python
Copy
# --------------------------
# backend/agent/planner_agent.py
# --------------------------
from openai import AzureOpenAI
from config import Config

class PlannerAgent:
    def __init__(self):
        self.client = AzureOpenAI(
            api_key=Config.AZURE_OPENAI_API_KEY,
            api_version=Config.AZURE_OPENAI_API_VERSION,
            azure_endpoint=Config.AZURE_OPENAI_ENDPOINT
        )
    
    def generate_plan(self, user_description: str) -> str:
        prompt = f"""Create a detailed flyer plan based on the following description:
        {user_description}
        
        Include the following elements:
        - Headline
        - Key visuals
        - Color scheme
        - Main content sections
        - Call-to-action
        - Special offers (if any)
        """
        
        response = self.client.chat.completions.create(
            model=Config.AZURE_DEPLOYMENT_NAME,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
    
    def regenerate_plan(self, feedback: str, previous_plan: str) -> str:
        prompt = f"""Previous plan: {previous_plan}
        
        User feedback: {feedback}
        
        Please regenerate the flyer plan incorporating the feedback while maintaining previous good elements."""
        
        response = self.client.chat.completions.create(
            model=Config.AZURE_DEPLOYMENT_NAME,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
python
Copy
# --------------------------
# backend/app.py
# --------------------------
from flask import Flask, render_template
from flask_socketio import SocketIO, emit
from agent.planner_agent import PlannerAgent

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*")

planner = PlannerAgent()
user_sessions = {}

@socketio.on('generate_plan')
def handle_generate_plan(data):
    session_id = request.sid
    plan = planner.generate_plan(data['description'])
    user_sessions[session_id] = {'current_plan': plan}
    emit('plan_created', {'plan': plan})

@socketio.on('approve_plan')
def handle_approve():
    session_id = request.sid
    emit('plan_approved', {'message': 'Plan approved! Thank you!'})

@socketio.on('reject_plan')
def handle_reject(data):
    session_id = request.sid
    feedback = data['feedback']
    previous_plan = user_sessions[session_id]['current_plan']
    new_plan = planner.regenerate_plan(feedback, previous_plan)
    user_sessions[session_id]['current_plan'] = new_plan
    emit('plan_updated', {'plan': new_plan})

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    socketio.run(app, debug=True)
html
Copy
<!-- -------------------------- -->
<!-- frontend/templates/index.html -->
<!-- -------------------------- -->
<!DOCTYPE html>
<html>
<head>
    <title>Flyer Planner</title>
    <style>
        .container { max-width: 800px; margin: 0 auto; padding: 20px; }
        .hidden { display: none; }
        .plan-box { border: 1px solid #ccc; padding: 15px; margin: 10px 0; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Flyer Planner</h1>
        
        <div id="inputSection">
            <textarea id="description" rows="5" placeholder="Enter your flyer description..."></textarea>
            <button onclick="submitDescription()">Generate Plan</button>
        </div>

        <div id="planSection" class="hidden">
            <div class="plan-box" id="planDisplay"></div>
            <button onclick="approvePlan()">Approve</button>
            <button onclick="showFeedback()">Disapprove</button>
            
            <div id="feedbackSection" class="hidden">
                <textarea id="feedback" placeholder="Enter your feedback..."></textarea>
                <button onclick="submitFeedback()">Submit Feedback</button>
            </div>
        </div>
        
        <div id="resultMessage"></div>
    </div>

    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <script>
        const socket = io.connect('http://' + document.domain + ':' + location.port);
        
        function submitDescription() {
            const description = document.getElementById('description').value;
            socket.emit('generate_plan', {description: description});
        }

        function approvePlan() {
            socket.emit('approve_plan');
        }

        function showFeedback() {
            document.getElementById('feedbackSection').classList.remove('hidden');
        }

        function submitFeedback() {
            const feedback = document.getElementById('feedback').value;
            socket.emit('reject_plan', {feedback: feedback});
        }

        // Socket listeners
        socket.on('plan_created', function(data) {
            document.getElementById('inputSection').classList.add('hidden');
            document.getElementById('planSection').classList.remove('hidden');
            document.getElementById('planDisplay').innerText = data.plan;
        });

        socket.on('plan_updated', function(data) {
            document.getElementById('planDisplay').innerText = data.plan;
            document.getElementById('feedbackSection').classList.add('hidden');
        });

        socket.on('plan_approved', function(data) {
            document.getElementById('resultMessage').innerHTML = 
                '<h3>✅ ' + data.message + '</h3>';
            document.getElementById('planSection').classList.add('hidden');
        });
    </script>
</body>
</html>
