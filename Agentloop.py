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
    input_description: str
    plan: str
    image: str
    image_feedback: str
    image_approved: bool
    text: dict
    text_feedback: str
    text_approved: bool
    final_flyer: np.ndarray

def planner_agent(state: FlyerState) -> FlyerState:
    print("🛠️ Planning flyer strategy...")
    response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[{
            "role": "system",
            "content": "Create detailed flyer plan including target audience, color scheme, imagery needs, and text tone."
        }, {
            "role": "user", 
            "content": state["input_description"]
        }]
    )
    state["plan"] = response.choices[0].message.content
    return state

def image_generator_agent(state: FlyerState) -> FlyerState:
    print("🎨 Generating flyer image...")
    messages = [{
        "role": "system",
        "content": "Create DALL-E prompt for flyer images based on design plan"
    }, {
        "role": "user",
        "content": state["plan"]
    }]
    
    if state.get("image_feedback"):
        messages.append({
            "role": "user",
            "content": f"Human feedback: {state['image_feedback']}"
        })
    
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

def text_analyser_agent(state: FlyerState) -> FlyerState:
    print("📝 Analyzing text content...")
    messages = [{
        "role": "system",
        "content": "Generate JSON with headline, subtext, and position based on plan"
    }, {
        "role": "user",
        "content": state["plan"]
    }]
    
    if state.get("text_feedback"):
        messages.append({
            "role": "user",
            "content": f"Human feedback: {state['text_feedback']}"
        })
    
    response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=messages,
        response_format={"type": "json_object"}
    )
    state["text"] = eval(response.choices[0].message.content)
    return state

def image_approval_node(state: FlyerState) -> FlyerState:
    print("\n=== IMAGE APPROVAL ===")
    print(f"Generated Image URL: {state['image']}")
    print("Please review the image above (open URL in browser)")
    
    approval = input("Approve this image? (Y/N): ").strip().upper()
    if approval == 'Y':
        state["image_approved"] = True
    else:
        state["image_approved"] = False
        state["image_feedback"] = input("Enter your feedback for improvement: ")
    
    return state

def text_approval_node(state: FlyerState) -> FlyerState:
    print("\n=== TEXT APPROVAL ===")
    print(f"Headline: {state['text']['headline']}")
    print(f"Subtext: {state['text']['subtext']}")
    print(f"Position: {state['text']['position']}")
    
    approval = input("Approve this text? (Y/N): ").strip().upper()
    if approval == 'Y':
        state["text_approved"] = True
    else:
        state["text_approved"] = False
        state["text_feedback"] = input("Enter your feedback for improvement: ")
    
    return state

def flyer_agent(state: FlyerState) -> FlyerState:
    print("🖼️ Composing final flyer...")
    response = requests.get(state["image"])
    img = Image.open(io.BytesIO(response.content)).convert("RGB")
    draw = ImageDraw.Draw(img)
    
    # Font setup and text positioning
    headline_font = ImageFont.truetype("arialbd.ttf", 72) if "arialbd.ttf" else ImageFont.load_default()
    subtext_font = ImageFont.truetype("arial.ttf", 48) if "arial.ttf" else ImageFont.load_default()
    
    position = state["text"]["position"]
    positions = {
        "top-left": (100, 100),
        "top-center": (img.width//2, 100),
        "center": (img.width//2, img.height//2),
        "bottom-center": (img.width//2, img.height-150)
    }
    x, y = positions.get(position, (100, 100))
    
    # Draw text elements
    for idx, (text, font) in enumerate([
        (state["text"]["headline"], headline_font),
        (state["text"]["subtext"], subtext_font)
    ]):
        bbox = draw.textbbox((x, y), text, font=font)
        draw.rectangle(bbox, fill=(0, 0, 0, 128))
        draw.text((x, y), text, font=font, fill="white")
        y += bbox[3] - bbox[1] + 20
    
    state["final_flyer"] = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    return state

def check_approvals(state: FlyerState) -> Literal["generate_flyer", "wait"]:
    if state.get("image_approved", False) and state.get("text_approved", False):
        return "generate_flyer"
    return "wait"

# Create workflow
workflow = StateGraph(FlyerState)

# Add nodes
workflow.add_node("planner", planner_agent)
workflow.add_node("image_gen", image_generator_agent)
workflow.add_node("text_analyser", text_analyser_agent)
workflow.add_node("image_approval", image_approval_node)
workflow.add_node("text_approval", text_approval_node)
workflow.add_node("check_approvals", check_approvals)
workflow.add_node("flyer", flyer_agent)

# Set up edges
workflow.add_edge("planner", "image_gen")
workflow.add_edge("planner", "text_analyser")

workflow.add_edge("image_gen", "image_approval")
workflow.add_edge("text_analyser", "text_approval")

workflow.add_conditional_edges(
    "image_approval",
    lambda s: "image_gen" if not s.get("image_approved") else "check_approvals"
)
workflow.add_conditional_edges(
    "text_approval",
    lambda s: "text_analyser" if not s.get("text_approved") else "check_approvals"
)

workflow.add_conditional_edges(
    "check_approvals",
    lambda s: "flyer" if s.get("image_approved") and s.get("text_approved") else END,
    {"generate_flyer": "flyer", "wait": END}
)

workflow.add_edge("flyer", END)
workflow.set_entry_point("planner")

app = workflow.compile()

# Execute
if __name__ == "__main__":
    inputs = {"input_description": "Tech conference for AI developers"}
    result = app.invoke(inputs)
    
    if "final_flyer" in result:
        output_path = f"final_flyer_{uuid.uuid4()}.png"
        cv2.imwrite(output_path, result["final_flyer"])
        print(f"✅ Final flyer saved to {output_path}")
    else:
        print("❌ Flyer creation process incomplete")
