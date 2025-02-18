from typing import TypedDict, Literal
from langgraph.graph import StateGraph, END
from openai import OpenAI
import requests
from PIL import Image, ImageDraw, ImageFont
import io
import numpy as np
import cv2
import uuid

client = OpenAI()

class FlyerState(TypedDict):
    # State components
    input_description: str
    plan: str
    plan_approved: bool
    plan_feedback: str
    image: str
    image_approved: bool
    image_feedback: str
    text: dict
    text_approved: bool
    text_feedback: str
    final_flyer: np.ndarray

# 1️⃣ Planner Agent with Feedback Loop
def planner_agent(state: FlyerState) -> FlyerState:
    print("\n🔧 Generating/Refining Plan...")
    messages = [
        {"role": "system", "content": "Expert flyer designer creating detailed plans"},
        {"role": "user", "content": state["input_description"]}
    ]
    
    if state.get("plan_feedback"):
        messages.append({"role": "user", "content": f"Feedback: {state['plan_feedback']}"})
    
    response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=messages
    )
    state["plan"] = response.choices[0].message.content
    return state

def plan_approval(state: FlyerState) -> FlyerState:
    print("\n=== PLAN APPROVAL ===")
    print(f"Generated Plan:\n{state['plan']}")
    approval = input("Approve this plan? (Y/N): ").strip().upper()
    
    if approval == 'Y':
        state["plan_approved"] = True
        state["plan_feedback"] = ""
    else:
        state["plan_approved"] = False
        state["plan_feedback"] = input("Enter your improvement feedback: ")
    
    return state

# 2️⃣ Image Generator with Feedback
def image_generator_agent(state: FlyerState) -> FlyerState:
    print("\n🎨 Generating/Refining Image...")
    messages = [
        {"role": "system", "content": "Create DALL-E prompts from plans"},
        {"role": "user", "content": state["plan"]}
    ]
    
    if state.get("image_feedback"):
        messages.append({"role": "user", "content": f"Feedback: {state['image_feedback']}"})
    
    prompt_response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=messages
    )
    image_prompt = prompt_response.choices[0].message.content
    
    image_response = client.images.generate(
        model="dall-e-3",
        prompt=image_prompt,
        size="1024x1024",
        quality="hd"
    )
    state["image"] = image_response.data[0].url
    return state

def image_approval(state: FlyerState) -> FlyerState:
    print("\n=== IMAGE APPROVAL ===")
    print(f"Image URL: {state['image']}")
    approval = input("Approve this image? (Y/N): ").strip().upper()
    
    if approval == 'Y':
        state["image_approved"] = True
        state["image_feedback"] = ""
    else:
        state["image_approved"] = False
        state["image_feedback"] = input("Enter image improvement feedback: ")
    
    return state

# 3️⃣ Text Analyzer with Feedback
def text_analyser_agent(state: FlyerState) -> FlyerState:
    print("\n📝 Generating/Refining Text...")
    messages = [
        {"role": "system", "content": "Generate JSON text elements"},
        {"role": "user", "content": state["plan"]}
    ]
    
    if state.get("text_feedback"):
        messages.append({"role": "user", "content": f"Feedback: {state['text_feedback']}"})
    
    response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=messages,
        response_format={"type": "json_object"}
    )
    state["text"] = eval(response.choices[0].message.content)
    return state

def text_approval(state: FlyerState) -> FlyerState:
    print("\n=== TEXT APPROVAL ===")
    print(f"Headline: {state['text']['headline']}")
    print(f"Subtext: {state['text']['subtext']}")
    approval = input("Approve this text? (Y/N): ").strip().upper()
    
    if approval == 'Y':
        state["text_approved"] = True
        state["text_feedback"] = ""
    else:
        state["text_approved"] = False
        state["text_feedback"] = input("Enter text improvement feedback: ")
    
    return state

# 4️⃣ Final Composition
def flyer_agent(state: FlyerState) -> FlyerState:
    print("\n🖼️ Creating Final Flyer...")
    # Image processing and text overlay logic
    response = requests.get(state["image"])
    img = Image.open(io.BytesIO(response.content)).convert("RGB")
    draw = ImageDraw.Draw(img)
    
    # Text positioning and rendering logic
    headline_font = ImageFont.truetype("arialbd.ttf", 72) if "arialbd.ttf" else ImageFont.load_default()
    subtext_font = ImageFont.truetype("arial.ttf", 48) if "arial.ttf" else ImageFont.load_default()
    
    # ... (text positioning and drawing logic)
    
    state["final_flyer"] = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    return state

# Conditional Routing Functions
def route_plan(state: FlyerState) -> str:
    return "plan_approval" if not state.get("plan_approved") else "planner"

def route_components(state: FlyerState) -> Literal["generate_flyer", "wait"]:
    if all([state.get("image_approved"), state.get("text_approved")]):
        return "generate_flyer"
    return "wait"

# Workflow Construction
workflow = StateGraph(FlyerState)

# Add Nodes
workflow.add_node("planner", planner_agent)
workflow.add_node("plan_approval", plan_approval)
workflow.add_node("image_gen", image_generator_agent)
workflow.add_node("image_approval", image_approval)
workflow.add_node("text_analyser", text_analyser_agent)
workflow.add_node("text_approval", text_approval)
workflow.add_node("check_approvals", route_components)
workflow.add_node("flyer", flyer_agent)

# Set Up Edges
workflow.set_entry_point("planner")

# Plan Approval Loop
workflow.add_edge("planner", "plan_approval")
workflow.add_conditional_edges(
    "plan_approval",
    lambda s: "planner" if not s.get("plan_approved") else "image_gen",
    {"planner": "planner", "image_gen": "image_gen"}
)

# Image Generation Loop
workflow.add_edge("image_gen", "image_approval")
workflow.add_conditional_edges(
    "image_approval",
    lambda s: "image_gen" if not s.get("image_approved") else "check_approvals"
)

# Text Generation Loop
workflow.add_edge("plan_approval", "text_analyser")
workflow.add_edge("text_analyser", "text_approval")
workflow.add_conditional_edges(
    "text_approval",
    lambda s: "text_analyser" if not s.get("text_approved") else "check_approvals"
)

# Final Composition
workflow.add_conditional_edges(
    "check_approvals",
    lambda s: "flyer" if s.get("image_approved") and s.get("text_approved") else "wait",
    {"generate_flyer": "flyer", "wait": END}
)
workflow.add_edge("flyer", END)

# Compile Workflow
app = workflow.compile()

# Execution Example
if __name__ == "__main__":
    inputs = {"input_description": "Summer Music Festival Flyer"}
    result = app.invoke(inputs)
    
    if "final_flyer" in result:
        output_path = f"flyer_{uuid.uuid4()}.png"
        cv2.imwrite(output_path, result["final_flyer"])
        print(f"✅ Final flyer saved to {output_path}")
    else:
        print("❌ Process incomplete")
