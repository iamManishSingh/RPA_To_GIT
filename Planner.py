from pydantic import BaseModel, Field
from typing import List, Dict

class TextGeneratorPlan(BaseModel):
    """Detailed specifications for textual elements generation"""
    primary_headline_requirements: str = Field(..., description="3-5 headline options focusing on key USP and emotional triggers")
    subtext_strategy: str = Field(..., description="Supporting text structure with conversion-focused messaging")
    key_features: List[str] = Field(..., min_items=3, description="List of product/service features to emphasize")
    tone_guidelines: str = Field(..., description="Specific tone requirements (e.g., professional, playful, urgent)")
    call_to_action: str = Field(..., description="Primary CTA phrasing with action verbs")
    legal_requirements: List[str] = Field(..., description="Mandatory disclaimers or compliance text")
    typography_preferences: List[str] = Field(..., description="Font pairing suggestions for hierarchy")
    text_layout_suggestions: str = Field(..., description="Recommended text placement and spacing")

class ImageGeneratorPlan(BaseModel):
    """Comprehensive visual requirements for flyer design"""
    visual_theme: str = Field(..., description="Central visual metaphor or theme (e.g., 'urban tech', 'organic wellness')")
    color_palette: Dict[str, str] = Field(..., description="Primary and secondary colors with hex codes")
    image_types: List[str] = Field(..., description="Required image categories (product shots, icons, backgrounds)")
    composition_requirements: str = Field(..., description="Layout structure and focal point placement")
    style_references: List[str] = Field(..., description="Specific visual styles (e.g., 'flat design', 'photorealistic')")
    branding_elements: List[str] = Field(..., description="Mandatory logos, watermarks, or mascots")
    aspect_ratio: str = Field(..., description="Required dimensions and orientation")
    image_text_integration: str = Field(..., description="How text should interact with images")

class FlyerGenerationPlan(BaseModel):
    text_plan: TextGeneratorPlan
    image_plan: ImageGeneratorPlan

PLANNER_AGENT_PROMPT = """
You are a Senior Marketing Strategist AI tasked with creating a coordinated flyer generation plan. Analyze the following requirements and create detailed specifications for both text and image agents:

**Client Brief:**
{client_brief}

**Strategic Planning Framework:**
1. Audience Analysis: Identify key demographic/psychographic factors
2. Conversion Goals: Primary action desired from viewers
3. Brand Consistency: Maintain {brand_name} visual/verbal identity
4. Information Hierarchy: Prioritize elements by importance
5. Cross-Modal Synergy: Ensure text/images reinforce each other

**Text Generation Plan Requirements:**
- Create headlines that work with planned visual focal points
- Subtext should complement without duplicating image messages
- Include power words aligned with {industry} best practices
- Optimize text length for scannability (F-shaped pattern)
- CTA must align with conversion funnel stage {funnel_stage}

**Image Generation Plan Requirements:**
- Visuals must create immediate emotional impact ({desired_emotion})
- Images should demonstrate {key_product_feature} clearly
- Include negative space for text overlay in {text_placement_areas}
- Follow {brand_name} photography/style guidelines
- Optimize for both print and digital viewing

**Output Requirements:**
- Text and image plans must share common conversion narrative
- Include specific cross-references between visual/text elements
- Balance information density with white space
- Compliance with {industry_regulations}
- Versioning for {target_platforms}

Provide final specifications in the required structured format.
"""
