from crewai import Agent
from langchain.chat_models import AzureChatOpenAI

class PlannerAgent:
    def __init__(self):
        self.llm = AzureChatOpenAI(
            openai_api_base=Config.AZURE_OPENAI_ENDPOINT,
            openai_api_version=Config.API_VERSION,
            deployment_name=Config.AZURE_DEPLOYMENT_NAME,
            openai_api_key=Config.AZURE_OPENAI_API_KEY,
            temperature=0.3
        )
    
    def create(self):
        return Agent(
            role='Creative Flyer Designer',
            goal='Generate innovative flyer designs based on user requirements',
            backstory='Expert in marketing and graphic design with years of experience creating compelling visuals',
            llm=self.llm,
            verbose=True
        )





backend/agents/human_feedback_agent.py

python
Copy
from crewai import Agent
from langchain.chat_models import AzureChatOpenAI

class HumanFeedbackAgent:
    def __init__(self):
        self.llm = AzureChatOpenAI(
            openai_api_base=Config.AZURE_OPENAI_ENDPOINT,
            openai_api_version=Config.API_VERSION,
            deployment_name=Config.AZURE_DEPLOYMENT_NAME,
            openai_api_key=Config.AZURE_OPENAI_API_KEY,
            temperature=0.3
        )
    
    def create(self):
        return Agent(
            role='Feedback Incorporator',
            goal='Modify flyer designs based on human feedback',
            backstory='Specialist in iterating designs based on user feedback',
            llm=self.llm,
            verbose=True
        )



backend/tasks/planning_tasks.py

python
Copy
from crewai import Task

class PlanningTasks:
    @staticmethod
    def create_initial_plan(agent):
        return Task(
            description="""Generate a detailed flyer plan based on user description.
            Include layout, color scheme, typography, key visuals, and call-to-action.
            User Description: {user_input}""",
            agent=agent,
            expected_output="A structured flyer plan in markdown format with sections for each design element."
        )

    @staticmethod
    def revise_plan(agent):
        return Task(
            description="""Revise the flyer plan based on user feedback.
            Original Plan: {original_plan}
            User Feedback: {feedback}""",
            agent=agent,
            expected_output="Revised flyer plan in markdown format addressing all feedback points."
        )


backend server.py

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from websockets import WebSocketServerProtocol
import asyncio
from agents.planner_agent import PlannerAgent
from agents.human_feedback_agent import HumanFeedbackAgent
from tasks.planning_tasks import PlanningTasks
from crewai import Crew
import json

app = FastAPI()
app.mount("/static", StaticFiles(directory="frontend"), name="static")

class ConnectionManager:
    def __init__(self):
        self.active_connections = []
    
    async def connect(self, websocket: WebSocketServerProtocol):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    async def send_message(self, message: str, websocket: WebSocketServerProtocol):
        await websocket.send_text(message)

manager = ConnectionManager()

async def process_input(user_input, feedback=None, original_plan=None):
    planner_agent = PlannerAgent().create()
    feedback_agent = HumanFeedbackAgent().create()
    
    if not feedback:
        task = PlanningTasks.create_initial_plan(planner_agent).format(user_input=user_input)
    else:
        task = PlanningTasks.revise_plan(feedback_agent).format(
            original_plan=original_plan,
            feedback=feedback
        )
    
    crew = Crew(
        agents=[planner_agent if not feedback else feedback_agent],
        tasks=[task],
        verbose=2
    )
    
    return crew.kickoff()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocketServerProtocol):
    await manager.connect(websocket)
    original_plan = None
    
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message['type'] == 'initial_request':
                user_input = message['content']
                plan = await process_input(user_input)
                original_plan = plan
                await manager.send_message(json.dumps({
                    'type': 'plan',
                    'content': plan
                }), websocket)
            
            elif message['type'] == 'feedback':
                feedback = message['content']
                revised_plan = await process_input(
                    feedback=feedback,
                    original_plan=original_plan
                )
                original_plan = revised_plan
                await manager.send_message(json.dumps({
                    'type': 'plan',
                    'content': revised_plan
                }), websocket)
    
    except Exception as e:
        print(f"Error: {e}")
        await websocket.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)



index.html
<!DOCTYPE html>
<html>
<head>
    <title>Flyer Planner</title>
    <style>
        .container { max-width: 800px; margin: 0 auto; padding: 20px; }
        #plan-display { border: 1px solid #ccc; padding: 20px; margin: 20px 0; }
        .feedback-section { display: none; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Flyer Planner</h1>
        <div id="input-section">
            <textarea id="user-input" rows="5" cols="80" placeholder="Describe your flyer requirements..."></textarea>
            <button onclick="submitRequest()">Generate Plan</button>
        </div>
        
        <div class="feedback-section" id="feedback-section">
            <div id="plan-display"></div>
            <textarea id="feedback-input" rows="3" cols="80" placeholder="Provide feedback..."></textarea>
            <button onclick="submitFeedback()">Submit Feedback</button>
        </div>
    </div>

    <script>
        const ws = new WebSocket('ws://localhost:8000/ws');
        
        ws.onmessage = function(event) {
            const data = JSON.parse(event.data);
            if (data.type === 'plan') {
                document.getElementById('plan-display').innerHTML = data.content.replace(/\n/g, '<br>');
                document.getElementById('feedback-section').style.display = 'block';
            }
        };

        function submitRequest() {
            const userInput = document.getElementById('user-input').value;
            ws.send(JSON.stringify({
                type: 'initial_request',
                content: userInput
            }));
        }

        function submitFeedback() {
            const feedback = document.getElementById('feedback-input').value;
            ws.send(JSON.stringify({
                type: 'feedback',
                content: feedback
            }));
            document.getElementById('feedback-input').value = '';
        }
    </script>
</body>
</html>


fastapi
uvicorn
websockets
python-dotenv
crewai
langchain
azure-openai

