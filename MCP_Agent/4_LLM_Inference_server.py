from fastmcp import FastMCP
from transformers import pipeline
import openvino_genai as ov_genai
import huggingface_hub as hf_hub
import sys
import os
import asyncio
import json
from typing import AsyncGenerator
from utils import load_config, setup_logging

# Load configuration
config = load_config()
logger = setup_logging(__name__)

# Initialize the MCP LLM Server
mcp = FastMCP(
    config['servers']['llm']['name'],
    host=config['servers']['llm']['host'],
    port=config['servers']['llm']['port']
)

# Device detection for Intel GPU support
def detect_best_device():
    """Detect the best available device for OpenVINO inference"""
    try:
        import openvino as ov
        core = ov.Core()
        available_devices = core.available_devices
        logger.info(f"Available OpenVINO devices: {available_devices}")
        
        # Prefer GPU (Intel iGPU/dGPU) if available, fallback to CPU
        if any("GPU" in device for device in available_devices):
            return "GPU"
        else:
            return "CPU"
    except Exception as e:
        logger.warning(f"Device detection failed: {e}, using CPU")
        return "CPU"

device = detect_best_device()
# device = "NPU"
logger.info(f"Selected device: {device}")
generator = None
model_type = None

try:
    # Try loading OpenVINO optimized Qwen model first
    model_name = "OpenVINO/qwen2.5-1.5b-instruct-int8-ov"
    model_path = "qwen2.5-1.5b-instruct-int8-ov"
    
    logger.info(f"Attempting to load OpenVINO model: {model_name}")
    logger.info("This may take several minutes for first-time download...")
    
    # Download model if not present
    if not os.path.exists(model_path):
        logger.info(f"Downloading model to {model_path}...")
        hf_hub.snapshot_download(model_name, local_dir=model_path)
    
    logger.info(f"Loading OpenVINO GenAI pipeline on {device}...")
    try:
        generator = ov_genai.LLMPipeline(model_path, device)
        gen_config = ov_genai.GenerationConfig()
        gen_config.max_new_tokens = 500
        logger.info(f"Successfully loaded OpenVINO Qwen model on {device}: {model_name}")
        model_type = "openvino"
    except Exception as device_error:
        if device == "GPU":
            logger.warning(f"GPU loading failed: {device_error}")
            logger.info("Falling back to CPU for OpenVINO...")
            generator = ov_genai.LLMPipeline(model_path, "CPU")
            logger.info(f"Successfully loaded OpenVINO Qwen model on CPU: {model_name}")
            model_type = "openvino"
        else:
            raise device_error
    
except Exception as qwen_error:
    logger.warning(f"Failed to load OpenVINO Qwen model: {qwen_error}")
    logger.info("Falling back to smaller DistilGPT-2 model...")
    
    try:
        # Fallback to smaller model using transformers
        model_name = "distilgpt2"
        
        generator = pipeline(
            "text-generation",
            model=model_name,
            device=-1,  # CPU only
            max_new_tokens=200,
            do_sample=True,
            temperature=0.7,
            pad_token_id=50256
        )
        
        logger.info(f"Successfully loaded fallback model: {model_name}")
        model_type = "transformers"
        
    except Exception as fallback_error:
        logger.error(f"Failed to load fallback model: {fallback_error}")
        generator = None
        model_type = None


class StreamingResponse:
    """Helper class to capture streaming tokens"""
    def __init__(self):
        self.tokens = []
        self.complete_text = ""
    
    def add_token(self, token):
        self.tokens.append(token)
        self.complete_text += token
        return False  # Continue generation


@mcp.tool()
async def safety_guidelines(weather_report: str, aqi_report: str) -> str:
    """
    Generate personalized outdoor safety and health guidelines
    based on the provided weather and air quality reports.

    This tool uses a language model to analyze the input data
    and provides an overall outdoor safety level.

    Args:
        weather_report (str): A detailed weather report for the location.
        aqi_report (str): The Air Quality Index (AQI) report for the same location.

    Returns:
        str: A formatted string containing the AI-generated safety advice,
        covering outdoor safety, health risks, precautions, and
        recommendations for sensitive groups.
    """
    if generator is None:
        return "The language model could not be initialized. Please check your model path and device setup."

    prompt = f"""
                You are a health assistant. Given this weather and air quality:

                Weather Report:
                {weather_report}

                AQI Report:
                {aqi_report}

                Provide:
                1. Overall outdoor safety level.
                2. Health risks.
                3. Precautions.
                4. Special advice for sensitive groups.

             """

    try:
        if model_type == "openvino":
            # OpenVINO GenAI API with improved streaming capture
            generation_config = ov_genai.GenerationConfig()
            generation_config.max_new_tokens = 300
            
            # Create streaming response handler
            streaming_response = StreamingResponse()
            
            def streamer(subword):
                # Print to server console (keep existing behavior)
                print(subword, end="", flush=True)
                sys.stdout.flush()
                
                # Capture for return to client
                streaming_response.add_token(subword)
                
                # Return flag corresponds whether generation should be stopped.
                # False means continue generation.
                return False
            
            # Generate with streaming
            result = generator.generate(prompt, generation_config, streamer)
            
            # Return the complete streamed response
            print()  # New line after streaming in console
            
            # Return the captured streaming text if available, otherwise the result
            if streaming_response.complete_text.strip():
                return streaming_response.complete_text.strip()
            else:
                return result.strip()
            
        elif model_type == "transformers":
            # Transformers pipeline API
            output = generator(prompt, max_new_tokens=200, do_sample=True, temperature=0.7, return_full_text=False)
            
            if not output or len(output) == 0:
                return "Failed to generate safety analysis. The model returned no valid output."

            result = output[0]["generated_text"]
            return result.strip()
        else:
            return "No model available for text generation."

    except Exception as e:
        return f"Model pipeline error: {str(e)}"


# New streaming endpoint for real-time token streaming
@mcp.tool()
async def safety_guidelines_streaming(weather_report: str, aqi_report: str) -> str:
    """
    Generate streaming safety guidelines with progressive token display.
    This version provides progressive text generation updates.
    """
    if generator is None:
        return "The language model could not be initialized. Please check your model path and device setup."

    prompt = f"""
                You are a health assistant. Given this weather and air quality:

                Weather Report:
                {weather_report}

                AQI Report:
                {aqi_report}

                Provide:
                1. Overall outdoor safety level.
                2. Health risks.
                3. Precautions.
                4. Special advice for sensitive groups.

             """

    try:
        if model_type == "openvino":
            generation_config = ov_genai.GenerationConfig()
            generation_config.max_new_tokens = 300
            
            # Collect tokens for progressive display
            accumulated_text = ""
            token_buffer = []
            
            def progressive_streamer(subword):
                nonlocal accumulated_text, token_buffer
                
                # Print to server console
                print(subword, end="", flush=True)
                sys.stdout.flush()
                
                # Buffer tokens for batch updates
                token_buffer.append(subword)
                accumulated_text += subword
                
                # Every few tokens, we could potentially send an update
                # For now, we'll just collect everything
                return False
            
            # Generate with progressive streaming
            result = generator.generate(prompt, generation_config, progressive_streamer)
            print()  # New line after streaming
            
            return accumulated_text.strip() if accumulated_text else result.strip()
            
        else:
            # Fall back to regular generation for non-OpenVINO models
            return await safety_guidelines(weather_report, aqi_report)
            
    except Exception as e:
        return f"Streaming model pipeline error: {str(e)}"


if __name__ == "__main__":
    mcp.run("sse")
