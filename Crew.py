# backend.py
from aiohttp import web
import asyncio
import json
from crewai import Agent, Task, Crew, Process

# ---------------------------
# WebSocket Server Setup
# ---------------------------
class ApprovalServer:
    def __init__(self):
        self.app = web.Application()
        self.app.router.add_get('/ws', self.websocket_handler)
        self.app['websockets'] = []
        self.pending_approvals = {}

    async def websocket_handler(self, request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        self.app['websockets'].append(ws)

        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                data = json.loads(msg.data)
                if data['type'] == 'approval_response':
                    approval_id = data['approval_id']
                    if approval_id in self.pending_approvals:
                        self.pending_approvals[approval_id].set_result(data['approved'])

        self.app['websockets'].remove(ws)
        return ws

    async def request_approval(self, content):
        approval_id = str(id(content))
        self.pending_approvals[approval_id] = asyncio.Future()

        await self.broadcast({
            'type': 'approval_request',
            'approval_id': approval_id,
            'content': content
        })

        approved = await self.pending_approvals[approval_id]
        del self.pending_approvals[approval_id]
        return approved

    async def broadcast(self, message):
        for ws in self.app['websockets']:
            await ws.send_json(message)

# ---------------------------
# CrewAI Implementation
# ---------------------------
class CrewManager:
    def __init__(self, server):
        self.server = server
        self.crew = None

    def setup_crew(self):
        # Define Agents
        planner = Agent(
            role="Marketing Strategist",
            goal="Create effective content plans",
            backstory="Expert in marketing campaigns",
            allow_delegation=False,
            verbose=True
        )

        writer = Agent(
            role="Copywriter",
            goal="Write compelling content",
            backstory="Award-winning promotional writer",
            verbose=True
        )

        # Define Tasks
        plan_task = Task(
            description="Create a detailed content plan for the flyer",
            agent=planner,
            expected_output="JSON structure with content sections and key messages",
            async_execution=False,
            execute_task=lambda agent, context: self.planning_logic(context)
        )

        content_task = Task(
            description="Generate final text content based on approved plan",
            agent=writer,
            expected_output="Complete text content with headline, body, and CTA",
            context=[plan_task],
            execute_task=lambda agent, context: self.content_logic(context)
        )

        # Setup Crew
        self.crew = Crew(
            agents=[planner, writer],
            tasks=[plan_task, content_task],
            process=Process.sequential,
            verbose=2
        )

    async def planning_logic(self, context):
        plan = {
            "sections": ["Header", "Benefits", "CTA"],
            "messages": ["New Product Launch", "50% Discount", "Limited Time Offer"]
        }
        
        approved = await self.server.request_approval({
            "type": "plan",
            "content": plan
        })
        
        if not approved:
            return await self.planning_logic(context)
        return plan

    async def content_logic(self, context):
        plan = context.get('planning_task', {})
        content = {
            "headline": "Revolutionary New Product!",
            "body": "Experience breakthrough technology with 50% discount",
            "cta": "Order Now →"
        }
        
        approved = await self.server.request_approval({
            "type": "content",
            "content": content
        })
        
        if not approved:
            return await self.content_logic(context)
        return content

    async def run_crew(self):
        if not self.crew:
            self.setup_crew()
        return await self.crew.kickoff()

# ---------------------------
# Main Execution
# ---------------------------
async def main():
    server = ApprovalServer()
    manager = CrewManager(server)
    
    # Start CrewAI process
    asyncio.create_task(manager.run_crew())
    
    await web._run_app(server.app, port=8080)

if __name__ == "__main__":
    asyncio.run(main())
