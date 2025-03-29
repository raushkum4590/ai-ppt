import streamlit as st
import google.generativeai as genai
import os
import requests
from PIL import Image
from io import BytesIO
import json
import base64
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="AI Image Generator",
    page_icon="🎨",
    layout="wide"
)

# App title and description
st.title("🖼️ AI Image Generator with Gemini")
st.markdown("Create amazing images using AI with the help of Google's Gemini")

# Initialize session state
if 'generated_images' not in st.session_state:
    st.session_state.generated_images = []
if 'prompts' not in st.session_state:
    st.session_state.prompts = []
if 'sd_api_key' not in st.session_state:
    st.session_state.sd_api_key = os.getenv("STABILITY_AI_API_KEY", "")
if 'gemini_api_key' not in st.session_state:
    st.session_state.gemini_api_key = os.getenv("GEMINI_API_KEY", "")
if 'gemini_model' not in st.session_state:
    st.session_state.gemini_model = "gemini-pro"

# Sidebar for configuration
with st.sidebar:
    st.header("Settings")
    
    # API key management with improved security
   
    # Help text for API keys
   
    # Gemini model selection
    st.subheader("Gemini Model")
    gemini_model = st.selectbox(
        "Select Gemini Model",
        ["gemini-2.0-flash-exp-image-generation", "gemini-2.0-flash"],
        index=0 if st.session_state.gemini_model == "gemini-pro" else 1
    )
    st.session_state.gemini_model = gemini_model
    
    st.subheader("Image Settings")
    image_size = st.selectbox("Image Size", [
        "1024x1024", "1152x896", "1216x832", "1344x768", "1536x640", 
        "640x1536", "768x1344", "832x1216", "896x1152"
    ])
    image_style = st.selectbox(
        "Style",
        ["Photorealistic", "Digital Art", "Anime", "Oil Painting", "Watercolor", "3D Render", "Cinematic"]
    )
    
    # Additional image generation settings
    st.subheader("Advanced Settings")
    cfg_scale = st.slider("CFG Scale (Creativity vs. Prompt Adherence)", 1, 20, 7, 
                         help="Higher values make image stick closer to prompt")
    steps = st.slider("Generation Steps", 10, 50, 30, 
                     help="More steps = higher quality but slower generation")
    
    st.markdown("---")
    st.caption("© 2023 AI Image Generator")

# Function to generate an image using Stable Diffusion API
def generate_image_with_sd(prompt, width, height, api_key, steps=30, cfg_scale=7):
    api_host = 'https://api.stability.ai'
    engine_id = 'stable-diffusion-xl-1024-v1-0'
    
    # Validate dimensions for SDXL model
    valid_dimensions = [
        (1024, 1024), (1152, 896), (1216, 832), (1344, 768), (1536, 640),
        (640, 1536), (768, 1344), (832, 1216), (896, 1152)
    ]
    
    # Check if dimensions are valid, otherwise default to 1024x1024
    if (width, height) not in valid_dimensions:
        st.warning(f"Dimensions {width}x{height} not supported by Stable Diffusion XL. Using 1024x1024 instead.")
        width, height = 1024, 1024
    
    if width > height:
        orientation = "landscape"
    elif height > width:
        orientation = "portrait"
    else:
        orientation = "square"
    
    response = requests.post(
        f"{api_host}/v1/generation/{engine_id}/text-to-image",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {api_key}"
        },
        json={
            "text_prompts": [
                {
                    "text": f"{prompt}, {image_style} style, high quality, detailed, {orientation}",
                    "weight": 1
                }
            ],
            "cfg_scale": cfg_scale,
            "height": height,
            "width": width,
            "samples": 4,  # Changed from 1 to 4
            "steps": steps,
        },
    )
    
    if response.status_code != 200:
        raise Exception(f"API request failed: {response.text}")
    
    data = response.json()
    images = []
    for artifact in data["artifacts"]:
        image_data = base64.b64decode(artifact["base64"])
        img = Image.open(BytesIO(image_data))
        images.append(img)
    return images  # Now returning a list of images

# Main area
if st.session_state.gemini_api_key:
    # Configure the Gemini API
    genai.configure(api_key=st.session_state.gemini_api_key)
    
    # Create tabs for different functions
    tab1, tab2 = st.tabs(["Generate", "History"])
    
    with tab1:
        st.header("Create Your Image")
        
        # Text prompt input
        user_prompt = st.text_area("Describe the image you want to create:", 
                          placeholder="A serene lake surrounded by mountains at sunset...",
                          height=100)
        
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col1:
            enhance_prompt = st.checkbox("Enhance my prompt with Gemini AI", value=True)
            
        with col2:
            quality = st.select_slider("Image Quality", ["Standard", "HD", "Ultra HD"])
            
        with col3:
            use_sd = st.checkbox("Use Stable Diffusion API", value=True, 
                               help="If checked, uses Stable Diffusion. Otherwise uses a placeholder.")
        
        # Generate button
        if st.button("Generate Image"):
            if user_prompt:
                try:
                    with st.spinner("Creating your images..."):  # Updated text
                        # Use Gemini to enhance the prompt if selected
                        if enhance_prompt:
                            model = genai.GenerativeModel(st.session_state.gemini_model)
                            enhancement_prompt = f"""
                            Enhance this image prompt for AI generation: "{user_prompt}"
                            
                            Create a detailed description with specific visual elements, style, lighting, 
                            colors, and composition. The image should be in {image_style} style.
                            
                            Provide ONLY the enhanced prompt with no introductions or explanations.
                            """
                            
                            response = model.generate_content(enhancement_prompt)
                            final_prompt = response.text.strip()
                            
                            # Show the enhanced prompt
                            st.subheader("Enhanced Prompt")
                            st.info(final_prompt)
                        else:
                            final_prompt = user_prompt
                        
                        # Parse image dimensions from selected size
                        width, height = map(int, image_size.split('x'))
                        
                        # Map quality settings to steps
                        quality_steps = {
                            "Standard": 20,
                            "HD": 30,
                            "Ultra HD": 50
                        }
                        
                        # Generate image using Stable Diffusion API if selected
                        if use_sd and st.session_state.sd_api_key:
                            images = generate_image_with_sd(
                                prompt=final_prompt,
                                width=width,
                                height=height,
                                api_key=st.session_state.sd_api_key,
                                steps=quality_steps[quality],
                                cfg_scale=cfg_scale
                            )
                        else:
                            # Fallback to Unsplash placeholder - create 4 images
                            images = []
                            for i in range(4):
                                st.warning("Using placeholder images. For AI-generated images, provide a Stable Diffusion API key.")
                                image_url = f"https://source.unsplash.com/random/{image_size.replace('x', '/')}/?{user_prompt.replace(' ', ',')}&sig={i}"  # Add sig parameter to get different images
                                response = requests.get(image_url)
                                img = Image.open(BytesIO(response.content))
                                images.append(img)
                        
                        # Store in history
                        st.session_state.generated_images.append(images)
                        st.session_state.prompts.append({
                            "original": user_prompt,
                            "enhanced": final_prompt if enhance_prompt else user_prompt,
                            "style": image_style
                        })
                        
                        # Display the images in a grid
                        st.subheader("Your Generated Images")
                        
                        # Display images in 2x2 grid
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.image(images[0], caption=f"Image 1 - {image_style} style", use_container_width=True)
                            buf = BytesIO()
                            images[0].save(buf, format="PNG")
                            st.download_button(
                                label="Download Image 1",
                                data=buf.getvalue(),
                                file_name="generated_image_1.png",
                                mime="image/png"
                            )
                        
                        with col2:
                            st.image(images[1], caption=f"Image 2 - {image_style} style", use_container_width=True)
                            buf = BytesIO()
                            images[1].save(buf, format="PNG")
                            st.download_button(
                                label="Download Image 2",
                                data=buf.getvalue(),
                                file_name="generated_image_2.png",
                                mime="image/png"
                            )
                        
                        col3, col4 = st.columns(2)
                        
                        with col3:
                            st.image(images[2], caption=f"Image 3 - {image_style} style", use_container_width=True)
                            buf = BytesIO()
                            images[2].save(buf, format="PNG")
                            st.download_button(
                                label="Download Image 3",
                                data=buf.getvalue(),
                                file_name="generated_image_3.png",
                                mime="image/png"
                            )
                        
                        with col4:
                            st.image(images[3], caption=f"Image 4 - {image_style} style", use_container_width=True)
                            buf = BytesIO()
                            images[3].save(buf, format="PNG")
                            st.download_button(
                                label="Download Image 4",
                                data=buf.getvalue(),
                                file_name="generated_image_4.png",
                                mime="image/png"
                            )
                        
                except Exception as e:
                    st.error(f"Error: {str(e)}")
                    st.info("If you're using Stable Diffusion API, check your API key and internet connection.")
            else:
                st.warning("Please enter a description for your image.")
    
    with tab2:
        st.header("Your Generated Images")
        
        if len(st.session_state.generated_images) > 0:
            for i in range(len(st.session_state.generated_images)-1, -1, -1):
                st.markdown(f"### Generation #{i+1}")
                st.markdown(f"**Original prompt:** {st.session_state.prompts[i]['original']}")
                if st.session_state.prompts[i]['enhanced'] != st.session_state.prompts[i]['original']:
                    st.markdown(f"**Enhanced prompt:** {st.session_state.prompts[i]['enhanced']}")
                st.markdown(f"**Style:** {st.session_state.prompts[i]['style']}")
                
                # Display all 4 images in a grid
                cols = st.columns(4)
                for idx, col in enumerate(cols):
                    with col:
                        if idx < len(st.session_state.generated_images[i]):
                            st.image(st.session_state.generated_images[i][idx], caption=f"Image {idx+1}", width=150)
                
                st.markdown("---")
        else:
            st.info("Your generated images will appear here after you create them.")
else:
    st.warning("Please enter your Google Gemini API key in the sidebar or add it to the .env file to get started.")
    
    # Sample display
    st.subheader("Sample Output")
    col1, col2 = st.columns(2)
    
    with col1:
        st.image("https://source.unsplash.com/random/600x400/?mountain,sunset", caption="Example: Mountain sunset", use_container_width=True)
        st.caption("Generate beautiful AI images after entering your API key")
        
    with col2:
        st.image("https://source.unsplash.com/random/600x400/?futuristic,city", caption="Example: Futuristic city", use_container_width=True)
        st.caption("Create any image you can imagine with text prompts")

# Add a footer with additional information
st.markdown("---")
st.markdown("""
### How to use this app:
1. Enter your API keys in the sidebar
2. Type a detailed description of the image you want to create
3. Select style and quality settings
4. Click "Generate Image"
5. Download your creation or find it later in History

For best results, provide detailed descriptions including subject, style, lighting, mood, and composition.
""")
