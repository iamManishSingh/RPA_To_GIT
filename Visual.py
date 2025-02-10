from typing import TypedDict
from langgraph.graph import StateGraph, END
from openai import OpenAI
import requests
from PIL import Image, ImageDraw, ImageFont
import io
import numpy as np
import cv2
import uuid

# Initialize OpenAI client
client = OpenAI()

# Define state structure
class FlyerState(TypedDict):
    input_description: str
    plan: str
    image: str
    text: dict
    final_flyer: np.ndarray

# 1️⃣ Planner Agent
def planner_agent(state: FlyerState) -> FlyerState:
    print("🛠️ Planning flyer strategy...")
    user_input = state["input_description"]
    
    # Generate flyer plan using LLM
    response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[
            {"role": "system", "content": """You're a professional flyer designer. Create a detailed plan including:
            1. Target audience analysis
            2. Color scheme recommendations
            3. Imagery requirements
            4. Text tone and style
            5. Layout suggestions"""},
            {"role": "user", "content": user_input}
        ]
    )
    
    state["plan"] = response.choices[0].message.content
    return state

# 2️⃣ Image Generator Agent
def image_generator_agent(state: FlyerState) -> FlyerState:
    print("🎨 Generating flyer image...")
    plan = state["plan"]
    
    # Generate image prompt from plan
    prompt_response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[
            {"role": "system", "content": "Create a detailed DALL-E prompt for flyer imagery based on the design plan"},
            {"role": "user", "content": plan}
        ]
    )
    image_prompt = prompt_response.choices[0].message.content
    
    # Generate image using DALL-E
    image_response = client.images.generate(
        model="dall-e-3",
        prompt=image_prompt,
        size="1024x1024",
        quality="hd",
        n=1,
    )
    
    state["image"] = image_response.data[0].url
    return state

# 3️⃣ TextAnalyser Agent
def text_analyser_agent(state: FlyerState) -> FlyerState:
    print("📝 Analyzing text content...")
    plan = state["plan"]
    
    # Generate text elements using LLM
    response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[
            {"role": "system", "content": """Generate flyer text elements:
            - Catchy headline (max 8 words)
            - Persuasive subtext (max 20 words)
            - Optimal text position (top-left, top-center, center, etc)
            Return JSON format with keys: headline, subtext, position"""},
            {"role": "user", "content": plan}
        ],
        response_format={"type": "json_object"}
    )
    
    state["text"] = eval(response.choices[0].message.content)
    return state

# 4️⃣ Flyer Agent
def flyer_agent(state: FlyerState) -> FlyerState:
    print("🖼️ Composing final flyer...")
    image_url = state["image"]
    text_elements = state["text"]
    
    # Download and process image
    response = requests.get(image_url)
    img = Image.open(io.BytesIO(response.content)).convert("RGB")
    
    # Create drawing context
    draw = ImageDraw.Draw(img)
    
    # Load fonts
    try:
        headline_font = ImageFont.truetype("arialbd.ttf", 72)
        subtext_font = ImageFont.truetype("arial.ttf", 48)
    except:
        headline_font = ImageFont.load_default()
        subtext_font = ImageFont.load_default()
    
    # Calculate positions
    img_width, img_height = img.size
    position_mapping = {
        "top-left": (img_width//10, img_height//10),
        "top-center": (img_width//2, img_height//10),
        "center": (img_width//2, img_height//2),
        "bottom-center": (img_width//2, img_height*0.9)
    }
    
    x, y = position_mapping.get(text_elements["position"], (img_width//10, img_height//10))
    
    # Draw text elements with background
    texts = [
        (text_elements["headline"], headline_font, (x, y)),
        (text_elements["subtext"], subtext_font, (x, y + 100))
    ]
    
    for text, font, (x, y) in texts:
        # Add text background
        bbox = draw.textbbox((x, y), text, font=font)
        draw.rectangle(bbox, fill=(0, 0, 0, 128))
        
        # Add text
        draw.text((x, y), text, font=font, fill=(255, 255, 255))
    
    # Convert to OpenCV format for final output
    state["final_flyer"] = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    return state

# Create workflow graph
workflow = StateGraph(FlyerState)

# Add nodes
workflow.add_node("planner", planner_agent)
workflow.add_node("image_gen", image_generator_agent)
workflow.add_node("text_analyser", text_analyser_agent)
workflow.add_node("flyer", flyer_agent)

# Set up edges
workflow.add_edge("planner", "image_gen")
workflow.add_edge("planner", "text_analyser")

# Conditional edges for final composition
def route_image(state):
    return "flyer" if "text" in state else END

def route_text(state):
    return "flyer" if "image" in state else END

workflow.add_conditional_edges("image_gen", route_image)
workflow.add_conditional_edges("text_analyser", route_text)
workflow.add_edge("flyer", END)

# Set entry point
workflow.set_entry_point("planner")

# Compile the graph
app = workflow.compile()

# Example usage
if __name__ == "__main__":
    inputs = {"input_description": "Create a flyer for a summer music festival featuring jazz and blues artists"}
    result = app.invoke(inputs)
    
    # Save and display result
    output_path = f"final_flyer_{uuid.uuid4()}.png"
    cv2.imwrite(output_path, result["final_flyer"])
    print(f"✅ Flyer saved to {output_path}")
